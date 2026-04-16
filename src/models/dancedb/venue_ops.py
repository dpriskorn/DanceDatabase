"""Venue operations: scrape, match, ensure exist."""

import json
import logging
import sys
import urllib.parse
from datetime import date

from wikibaseintegrator.wbi_config import config as wbi_config

import config
from src.models.bygdegardarna.scrape import scrape
from src.models.dancedb.client import DancedbClient
from src.models.danslogen.fuzzy import fuzzy_match_qid
from src.utils.coords import parse_coords
from src.utils.fuzzy import normalize_for_fuzzy
from src.utils.google_maps import GoogleMaps
from src.utils.qid import Qid

logger = logging.getLogger(__name__)


def require_tty():
    """Ensure running in interactive terminal."""
    if not sys.stdin.isatty():
        raise RuntimeError(
            "This operation requires an interactive terminal.\n"
            "No TTY detected. Please run interactively."
        )
    return True


def create_venue(venue_name: str, lat: float, lng: float, external_ids: dict[str, str] | None = None, client=None) -> str | None:
    """Create a new venue in DanceDB."""
    if client is None:
        client = DancedbClient()
    return client.create_venue(venue_name=venue_name, latitude=lat, longitude=lng, external_ids=external_ids)


def scrape_bygdegardarna(date_str: str | None = None) -> None:
    """Fetch venues from bygdegardarna.se with coordinates."""
    date_str = date_str or date.today().strftime("%Y-%m-%d")
    print("\n=== Scrape bygdegardarna venues ===")

    venues = scrape()
    print(f"Found {len(venues)} venues")

    output_file = config.bygdegardarna_dir / f"{date_str}.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(venues, f, ensure_ascii=False, indent=2)

    print(f"Saved to {output_file}")


def scrape_dancedb_venues(date_str: str | None = None) -> None:
    """Fetch existing venues from DanceDB via SPARQL."""
    import json

    from wikibaseintegrator.wbi_helpers import execute_sparql_query

    date_str = date_str or date.today().strftime("%Y-%m-%d")
    print("\n=== Scrape DanceDB venues ===")

    sparql = """
    PREFIX dd: <https://dance.wikibase.cloud/entity/>
    PREFIX ddt: <https://dance.wikibase.cloud/prop/direct/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

    SELECT ?item ?itemLabel (GROUP_CONCAT(?svAlias; SEPARATOR = "|") AS ?aliasStr) ?geo WHERE {
      ?item ddt:P1 dd:Q20 .
      OPTIONAL { ?item rdfs:label ?svLabel FILTER(LANG(?svLabel) = "sv") }
      OPTIONAL { ?item skos:altLabel ?svAlias FILTER(LANG(?svAlias) = "sv") }
      OPTIONAL { ?item ddt:P4 ?geo }
      BIND(COALESCE(?svLabel, "") AS ?itemLabel)
    }
    GROUP BY ?item ?itemLabel ?geo
    ORDER BY ?itemLabel
    LIMIT 2000
    """
    results = execute_sparql_query(query=sparql)
    venues = {}
    for binding in results["results"]["bindings"]:
        qid = binding["item"]["value"].rsplit("/", 1)[-1]
        label = binding.get("itemLabel", {}).get("value", "")

        alias_str = binding.get("aliasStr", {}).get("value", "")
        aliases = [a.lower() for a in alias_str.split("|") if a] if alias_str else []

        geo = binding.get("geo", {}).get("value", "")
        lat, lng = None, None
        if geo:
            coords = geo.replace("Point(", "").replace(")", "").split(" ")
            lng, lat = float(coords[0]), float(coords[1])

        venue_data = {"label": label, "lat": lat, "lng": lng, "aliases": aliases}
        venues[qid] = venue_data

    print(f"Found {len(venues)} venues")

    output_file = config.dancedb_dir / "venues" / f"{date_str}.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(venues, f, ensure_ascii=False, indent=2)

    print(f"Saved to {output_file}")


def match_venues(date_str: str | None = None, skip_prompts: bool = False) -> None:
    """Match bygdegardarna venues to DanceDB."""
    date_str = date_str or date.today().strftime("%Y-%m-%d")
    print("\n=== Match venues to DanceDB ===")

    byg_path = config.bygdegardarna_dir / f"{date_str}.json"
    db_path = config.dancedb_dir / "venues" / f"{date_str}.json"

    if not byg_path.exists():
        print(f"Error: bygdegardarna data not found: {byg_path}")
        return

    if not db_path.exists():
        print(f"Error: DanceDB venues not found: {db_path}")
        return

    byg_venues = json.loads(byg_path.read_text())
    db_venues = json.loads(db_path.read_text())

    db_labels = {v["label"].lower(): qid for qid, v in db_venues.items()}

    enriched = []
    unmatched = []
    matched_count = 0

    for venue in byg_venues:
        title = venue.get("title", "")
        title_lower = title.lower()

        if title_lower in db_labels:
            venue["qid"] = db_labels[title_lower]
            enriched.append(venue)
            matched_count += 1
        else:
            fuzzy = fuzzy_match_qid(title, db_labels, remove_terms=config.FUZZY_REMOVE_TERMS_BYGDEGARDARNA)
            if fuzzy and fuzzy.score >= config.FUZZY_THRESHOLD_VENUE_BYGDEGARDARNA:
                venue["qid"] = fuzzy.qid
                enriched.append(venue)
                matched_count += 1
                ff_warn = " ⚠️ FALSE FRIEND" if fuzzy.false_friend else ""
                logger.info(f"Fuzzy matched '{title}' to '{fuzzy.matched_label}' (input='{fuzzy.cleaned_input}', score={fuzzy.score:.1f}{ff_warn})")
            else:
                unmatched.append(venue)

    print(f"Matched: {matched_count} venues")
    print(f"Unmatched: {len(unmatched)} venues")

    enriched_file = config.enrich_dir / f"{date_str}.json"
    enriched_file.parent.mkdir(parents=True, exist_ok=True)
    with open(enriched_file, "w") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)

    unmatched_file = config.bygdegardarna_dir / "unmatched" / f"{date_str}.json"
    unmatched_file.parent.mkdir(parents=True, exist_ok=True)
    with open(unmatched_file, "w") as f:
        json.dump(unmatched, f, ensure_ascii=False, indent=2)

    print(f"Saved to {enriched_file}")


def ensure_venues(date_str: str | None = None) -> None:
    """Ensure danslogen venues exist in DanceDB before uploading events."""
    require_tty()  # Must run interactively
    from datetime import datetime

    import questionary
    from rapidfuzz import process as fuzz_process

    date_str = date_str or date.today().strftime("%Y-%m-%d")
    month_name = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B").lower()
    print(f"\n=== Ensuring venues exist for {date_str} ===")

    dansevents_file = config.danslogen_dir / "events" / f"{date_str}-{month_name}.json"
    if not dansevents_file.exists():
        print(f"Error: danslogen data not found: {dansevents_file}")
        return

    bygdegardarna_dir = config.data_dir / "bygdegardarna" / "enriched"
    bygdegardarna_venues = {}
    bygdegardarna_names = []
    if bygdegardarna_dir.exists():
        bygdegardarna_files = sorted(bygdegardarna_dir.glob("*.json"), reverse=True)
        if bygdegardarna_files:
            bygdegardarna_file = bygdegardarna_files[0]
            bygdegardarna_data = json.loads(bygdegardarna_file.read_text())
            bygdegardarna_venues = {v["title"].lower(): v for v in bygdegardarna_data if v.get("qid")}
            bygdegardarna_names = list(bygdegardarna_venues.keys())
            bygdegardarna_cities = {}
            for v in bygdegardarna_data:
                city = v.get("meta", {}).get("city", "").lower()
                if city and v.get("qid"):
                    position = v.get("position", {})
                    address = v.get("meta", {}).get("address", "")
                    gmaps = GoogleMaps(address=address, lat=position.get("lat"), lng=position.get("lng"))
                    v["gmaps_url"] = gmaps.url
                    bygdegardarna_cities[city] = v
            print(f"Loaded {len(bygdegardarna_venues)} bygdegardarna venues ({len(bygdegardarna_cities)} cities) for auto-match")

    folketshus_dir = config.data_dir / "folketshus" / "enriched"
    folketshus_venues = {}
    folketshus_names = []
    if folketshus_dir.exists():
        folketshus_files = sorted(folketshus_dir.glob("*.json"), reverse=True)
        if folketshus_files:
            folketshus_file = folketshus_files[0]
            folketshus_data = json.loads(folketshus_file.read_text())
            for v in folketshus_data:
                address = v.get("address", "")
                lat = v.get("lat")
                lng = v.get("lng")
                gmaps = GoogleMaps(address=address, lat=lat, lng=lng)
                v["gmaps_url"] = gmaps.url
            folketshus_venues = {v["name"].lower(): v for v in folketshus_data}
            folketshus_names = list(folketshus_venues.keys())
            print(f"Loaded {len(folketshus_venues)} folketshus venues for auto-match")

    from wikibaseintegrator.wbi_helpers import execute_sparql_query

    wbi_config["User-Agent"] = "DanceDB/1.0 (User:So9q)"

    sparql = """
    PREFIX dd: <https://dance.wikibase.cloud/entity/>
    PREFIX ddt: <https://dance.wikibase.cloud/prop/direct/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?item ?itemLabel ?alias ?geo WHERE {
      ?item ddt:P1 dd:Q20 .
      OPTIONAL { ?item rdfs:label ?itemLabel FILTER(LANG(?itemLabel) = "sv") }
      OPTIONAL { ?item rdfs:alias ?alias FILTER(LANG(?alias) = "sv") }
      OPTIONAL { ?item ddt:P4 ?geo }
    }
    """
    results = execute_sparql_query(query=sparql)
    existing_venues = {}
    for binding in results["results"]["bindings"]:
        qid = binding["item"]["value"].rsplit("/", 1)[-1]
        label = binding.get("itemLabel", {}).get("value", "")
        alias = binding.get("alias", {}).get("value", "")
        geo = binding.get("geo", {}).get("value", "")
        lat, lng = None, None
        if geo:
            coords = geo.replace("Point(", "").replace(")", "").split(" ")
            lng, lat = float(coords[0]), float(coords[1])
        label_lower = label.lower()
        if label_lower not in existing_venues:
            existing_venues[label_lower] = {"qid": qid, "lat": lat, "lng": lng, "aliases": []}
        if alias:
            existing_venues[label_lower].setdefault("aliases", []).append(alias.lower())

    print(f"Found {len(existing_venues)} existing venues in DanceDB")

    venue_mappings_file = config.data_dir / "dancedb" / "venue_mappings.jsonl"
    if venue_mappings_file.exists():
        print(f"Loading venue mappings from {venue_mappings_file.name}...")
        with open(venue_mappings_file) as f:
            for line in f:
                if line.strip():
                    try:
                        mapping = json.loads(line)
                        name = mapping.get("venue_name", "").lower()
                        qid = mapping.get("qid", "")
                        lat = mapping.get("lat")
                        lng = mapping.get("lng")
                        if name and qid and lat and lng and name not in existing_venues:
                            existing_venues[name] = {"qid": qid, "lat": lat, "lng": lng, "aliases": []}
                    except json.JSONDecodeError:
                        continue
        print(f"Loaded {len(existing_venues)} venues (including mappings)")

    bygdegardarna_addresses = {}
    bygdegardarna_files_to_check = []
    
    enriched_dir = config.bygdegardarna_dir / "enriched"
    if enriched_dir.exists():
        bygdegardarna_files_to_check.extend(sorted(enriched_dir.glob("*.json"), reverse=True))
    
    raw_dir = config.bygdegardarna_dir
    if raw_dir.exists():
        bygdegardarna_files_to_check.extend(sorted(raw_dir.glob("*.json"), reverse=True))
    
    seen_addresses = set()
    for byg_file in bygdegardarna_files_to_check:
        bygdegardarna_data = json.loads(byg_file.read_text())
        for v in bygdegardarna_data:
            title = v.get("title", "").lower()
            meta = v.get("meta", {})
            address = meta.get("address", "").lower()
            position = v.get("position", {})
            if title and address and position.get("lat") and address not in seen_addresses:
                seen_addresses.add(address)
                qid = v.get("qid", "")
                gmaps = GoogleMaps(address=address, lat=position["lat"], lng=position["lng"])
                gmaps_url = gmaps.url
                permalink = meta.get("permalink", "")
                if qid:
                    bygdegardarna_addresses[title] = {"qid": qid, "lat": position["lat"], "lng": position["lng"], "address": address, "gmaps_url": gmaps_url, "permalink": permalink}
                bygdegardarna_addresses[address] = {"lat": position["lat"], "lng": position["lng"], "address": address, "qid": qid, "gmaps_url": gmaps_url, "permalink": permalink}
    
    print(f"Loaded {len(bygdegardarna_addresses)} bygdegardarna addresses for address matching")

    events = json.loads(dansevents_file.read_text())
    venues_needed = set(e.get("location") for e in events if e.get("location"))
    print(f"Need venues for {len(venues_needed)} unique locations")

    step1_done = False
    step2_done = False

    new_venues = []
    matched = 0
    for venue_name in venues_needed:
        venue_lower = venue_name.lower()
        if venue_lower in existing_venues:
            matched += 1
            
            venue_mapping_file = config.data_dir / "dancedb" / "venue_mappings.jsonl"
            venue_mapping_file.parent.mkdir(parents=True, exist_ok=True)
            existing = existing_venues[venue_lower]
            gmaps = GoogleMaps(lat=existing.get("lat"), lng=existing.get("lng"))
            with open(venue_mapping_file, "a") as f:
                f.write(json.dumps({"venue_name": venue_name, "qid": existing["qid"], "lat": existing.get("lat"), "lng": existing.get("lng"), "gmaps_url": gmaps.url, "created_at": date_str}) + "\n")
            continue

        if not step1_done:
            logger.info("Step 1: Exact matches in DanceDB")
            step1_done = True

        folkets_match = False
        if folketshus_names:
            if not step2_done:
                logger.info(f"Step 2: Fuzzy matching against {len(folketshus_names)} folketshus venues (threshold {config.FUZZY_THRESHOLD_VENUE_FOLKETSHUS}%)...")
                step2_done = True
            
            folketshus_normalized = {normalize_for_fuzzy(n, config.FUZZY_REMOVE_TERMS_FOLKETSHUS): n for n in folketshus_names}
            fuzzy_folkets = fuzz_process.extractOne(
                normalize_for_fuzzy(venue_lower, config.FUZZY_REMOVE_TERMS_FOLKETSHUS),
                folketshus_normalized.keys(),
                score_cutoff=config.FUZZY_THRESHOLD_VENUE_FOLKETSHUS
            )
            if fuzzy_folkets:
                folkets_original = folketshus_normalized[fuzzy_folkets[0]]
                folkets_match = folketshus_venues[folkets_original]
                existing_venues[venue_lower] = {
                    "qid": folkets_match.get("qid", ""),
                    "lat": folkets_match.get("lat"),
                    "lng": folkets_match.get("lng"),
                    "aliases": [],
                }
                logger.info(f"Matched '{venue_name}' to folketshus '{folkets_original}' ({fuzzy_folkets[1]}%)")
                matched += 1
                
                venue_mapping_file = config.data_dir / "dancedb" / "venue_mappings.jsonl"
                venue_mapping_file.parent.mkdir(parents=True, exist_ok=True)
                with open(venue_mapping_file, "a") as f:
                    f.write(json.dumps({"venue_name": venue_name, "qid": folkets_match.get("qid", ""), "lat": folkets_match.get("lat"), "lng": folkets_match.get("lng"), "gmaps_url": folkets_match.get("gmaps_url", ""), "created_at": date_str}) + "\n")
                continue

        if bygdegardarna_names:
            if not step2_done:
                logger.info(f"Step 3: Fuzzy matching against {len(bygdegardarna_names)} bygdegardarna venues (threshold {config.FUZZY_THRESHOLD_VENUE_BYGDEGARDARNA}%)...")
                step2_done = True
            
            bygdegardarna_normalized = {normalize_for_fuzzy(n, config.FUZZY_REMOVE_TERMS_BYGDEGARDARNA): n for n in bygdegardarna_names}
            fuzzy_byg = fuzz_process.extractOne(
                normalize_for_fuzzy(venue_lower, config.FUZZY_REMOVE_TERMS_BYGDEGARDARNA),
                bygdegardarna_normalized.keys(),
                score_cutoff=config.FUZZY_THRESHOLD_VENUE_BYGDEGARDARNA
            )
            if fuzzy_byg:
                byg_original = bygdegardarna_normalized[fuzzy_byg[0]]
                byg_match = bygdegardarna_venues[byg_original]
                existing_venues[venue_lower] = {
                    "qid": byg_match["qid"],
                    "lat": byg_match.get("lat"),
                    "lng": byg_match.get("lng"),
                    "aliases": [],
                }
                logger.info(f"Matched '{venue_name}' to bygdegardarna '{byg_original}' ({fuzzy_byg[1]}%)")
                matched += 1
                
                venue_mapping_file = config.data_dir / "dancedb" / "venue_mappings.jsonl"
                venue_mapping_file.parent.mkdir(parents=True, exist_ok=True)
                with open(venue_mapping_file, "a") as f:
                    f.write(json.dumps({"venue_name": venue_name, "qid": byg_match.get("qid", ""), "lat": byg_match.get("lat"), "lng": byg_match.get("lng"), "gmaps_url": byg_match.get("gmaps_url", ""), "created_at": date_str}) + "\n")
                continue

        if bygdegardarna_addresses:
            for addr_key, addr_data in bygdegardarna_addresses.items():
                if venue_lower in addr_key or addr_key in venue_lower:
                    gmaps_url = addr_data.get("gmaps_url", "")
                    permalink = addr_data.get("permalink", "")
                    url_info = f"bygdegardarna.se: {permalink}" if permalink else f"Google: {gmaps_url}"
                    confirm = questionary.select(
                        f"Match '{venue_name}' to bygdegardarna address '{addr_data.get('address')}'?\n→ {url_info}",
                        choices=["Yes (Recommended)", "No", "Abort"],
                    ).ask()
                    if confirm == "No":
                        continue
                    elif confirm == "Abort":
                        print("Aborting...")
                        sys.exit(0)
                    existing_venues[venue_lower] = {
                        "qid": addr_data.get("qid", ""),
                        "lat": addr_data.get("lat"),
                        "lng": addr_data.get("lng"),
                        "aliases": [],
                    }
                    logger.info(f"Matched '{venue_name}' to bygdegardarna address '{addr_data.get('address')}'")
                    matched += 1
                    
                    venue_mapping_file = config.data_dir / "dancedb" / "venue_mappings.jsonl"
                    venue_mapping_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(venue_mapping_file, "a") as f:
                        f.write(json.dumps({"venue_name": venue_name, "qid": addr_data.get("qid", ""), "lat": addr_data.get("lat"), "lng": addr_data.get("lng"), "gmaps_url": gmaps_url, "permalink": permalink, "created_at": date_str}) + "\n")
                    break
            else:
                matched_city = False
                if bygdegardarna_cities:
                    city_matches = []
                    for city, city_venue in bygdegardarna_cities.items():
                        if city in venue_lower or venue_lower in city:
                            city_matches.append((city, city_venue))
                    if city_matches:
                        city_venue = city_matches[0][1]
                        gmaps_url = city_venue.get("gmaps_url", "")
                        meta = city_venue.get("meta", {})
                        permalink = meta.get("permalink", "") or city_venue.get("permalink", "")
                        url_info = f"bygdegardarna.se: {permalink}" if permalink else f"Google: {gmaps_url}"
                        confirm = questionary.select(
                            f"Match '{venue_name}' to bygdegardarna city '{city_matches[0][0]}'?\n→ {url_info}",
                            choices=["Yes (Recommended)", "No", "Abort"],
                        ).ask()
                        if confirm == "No":
                            continue
                        elif confirm == "Abort":
                            print("Aborting...")
                            sys.exit(0)
                        city, city_venue = city_matches[0]
                        existing_venues[venue_lower] = {
                            "qid": city_venue.get("qid", ""),
                            "lat": city_venue.get("lat"),
                            "lng": city_venue.get("lng"),
                            "aliases": [],
                        }
                        logger.info(f"Matched '{venue_name}' to bygdegardarna city '{city}'")
                        matched_city = True
                        matched += 1

                        venue_mapping_file = config.data_dir / "dancedb" / "venue_mappings.jsonl"
                        venue_mapping_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(venue_mapping_file, "a") as f:
                            f.write(json.dumps({"venue_name": venue_name, "qid": city_venue.get("qid", ""), "lat": city_venue.get("lat"), "lng": city_venue.get("lng"), "gmaps_url": city_venue.get("gmaps_url", ""), "permalink": city_venue.get("permalink", ""), "created_at": date_str}) + "\n")

                if not matched_city:
                    new_venues.append(venue_name)
        else:
            new_venues.append(venue_name)

    print(f"Matched: {matched}")
    print(f"Need to create: {len(new_venues)}")

    if not new_venues:
        print("All venues exist in DanceDB!")
        return

    print(f"\nMissing venues: {new_venues}")

    db_client = None
    if new_venues:
        print("Logging in to DanceDB...")
        db_client = DancedbClient()
        print("Logged in.")

    for venue_name in new_venues:
        print(f"\n--- Creating venue: {venue_name} ---")

        folketshus_match = None
        venue_lower = venue_name.lower()
        if folketshus_names:
            folketshus_normalized = {normalize_for_fuzzy(n, config.FUZZY_REMOVE_TERMS_FOLKETSHUS): n for n in folketshus_names}
            fuzzy = fuzz_process.extractOne(
                normalize_for_fuzzy(venue_lower, config.FUZZY_REMOVE_TERMS_FOLKETSHUS),
                folketshus_normalized.keys(),
                score_cutoff=config.FUZZY_THRESHOLD_VENUE_FOLKETSHUS
            )
            if fuzzy:
                folkets_original = folketshus_normalized[fuzzy[0]]
                folketshus_match = folketshus_venues[folkets_original]
                folketshus_match = folketshus_venues[fuzzy[0]]
                print(f"Found in folketshus: {fuzzy[0]} ({fuzzy[1]}, external_id: {folketshus_match['external_id']})")

        gmaps = f'https://www.google.com/maps/search/{urllib.parse.quote(venue_name, safe="")}'
        osm = f'https://www.openstreetmap.org/search?query={urllib.parse.quote(venue_name, safe="")}'
        print(f"Google: {gmaps}")

        if folketshus_match:
            use_coords = questionary.select(
                f"Use folketshus coordinates ({folketshus_match['lat']}, {folketshus_match['lng']})?",
                choices=["Yes (Recommended)", "No", "Abort"],
            ).ask()
            if use_coords == "Yes (Recommended)":
                coords = {"lat": folketshus_match["lat"], "lng": folketshus_match["lng"]}
            elif use_coords == "Abort":
                print("Aborting...")
                sys.exit(0)

        if not folketshus_match or not coords:
            print("Enter coordinates (lat, lng) or press Enter to skip:")
            coords_input = input("> ").strip()
            if coords_input:
                coords = parse_coords(coords_input)
                if not coords:
                    print("Invalid format, skipping")

        if not coords:
            print("Skipping venue creation (no coordinates)")
            continue

        external_ids = None
        if folketshus_match:
            external_ids = {"P44": folketshus_match["external_id"]}

        qid = create_venue(venue_name, coords["lat"], coords["lng"], external_ids=external_ids, client=db_client)
        if qid:
            print(f"Created: https://dance.wikibase.cloud/wiki/Item:{qid}")
            existing_venues[venue_name.lower()] = {"qid": qid, "lat": coords["lat"], "lng": coords["lng"]}

            venue_mapping_file = config.data_dir / "dancedb" / "venue_mappings.jsonl"
            venue_mapping_file.parent.mkdir(parents=True, exist_ok=True)
            with open(venue_mapping_file, "a") as f:
                f.write(json.dumps({"venue_name": venue_name, "qid": qid, "lat": coords["lat"], "lng": coords["lng"], "created_at": date_str}) + "\n")
            print(f"  -> Saved mapping to {venue_mapping_file.name}")
        else:
            print("Failed to create venue")

    print("\nVenue matching done. Run 'cli.py upload-events' to process events.")


def onbeat_ensure_venues(date_str: str | None = None, dry_run: bool = False) -> None:
    """Ensure onbeat venues exist in DanceDB."""
    import json
    from pathlib import Path

    import questionary

    date_str = date_str or date.today().strftime("%Y-%m-%d")
    print(f"\n=== Ensuring onbeat venues exist for {date_str} ===")

    onbeat_file = Path(f"data/onbeat/{date_str}.json")
    if not onbeat_file.exists():
        print(f"Error: onbeat data not found: {onbeat_file}")
        print("Run 'scrape-onbeat' first to fetch events.")
        return

    onbeat_data = json.loads(onbeat_file.read_text())
    events = onbeat_data.get("events", [])
    print(f"Loaded {len(events)} events from {onbeat_file}")

    dancedb_file = Path("data/dancedb/venues/2026-04-12.json")
    if dancedb_file.exists():
        dancedb_venues = json.loads(dancedb_file.read_text())
    else:
        dancedb_venues = {}
    print(f"Loaded {len(dancedb_venues)} venues from DanceDB")

    folketshus_file = Path("data/folketshus/enriched/2026-04-14.json")
    if folketshus_file.exists():
        folketshus_data = json.loads(folketshus_file.read_text())
        folketshus_venues = {v["name"].lower(): v for v in folketshus_data if v.get("qid")}
    else:
        folketshus_venues = {}
    print(f"Loaded {len(folketshus_venues)} venues from Folketshus")

    bygdegard_file = Path("data/bygdegardarna/2026-04-14.json")
    if bygdegard_file.exists():
        bygdegard_venues = json.loads(bygdegard_file.read_text())
    else:
        bygdegard_venues = []
    print(f"Loaded {len(bygdegard_venues)} venues from Bygdegardarna")

    venues_needed: dict[str, dict] = {}
    for event in events:
        venue_name = event.get("location", "")
        if not venue_name:
            continue

        venue_qid = event.get("venue_qid", "")
        if venue_qid:
            continue

        if venue_name not in venues_needed:
            venues_needed[venue_name] = {"source": None, "coords": None, "external_id": None}

    print(f"Found {len(venues_needed)} venues needing QIDs")

    if not venues_needed:
        print("All venues have QIDs!")
        return

    for venue_name, info in venues_needed.items():
        venue_lower = venue_name.lower()

        matched = False
        for qid, v in dancedb_venues.items():
            label = v.get("label", "").lower()
            if venue_lower in label or label in venue_lower:
                print(f"  {venue_name} -> DanceDB: {v['label']} ({qid})")
                info["source"] = "dancedb"
                info["qid"] = qid
                matched = True
                break
            aliases = v.get("aliases", [])
            for alias in aliases:
                if venue_lower in alias or alias in venue_lower:
                    print(f"  {venue_name} -> DanceDB alias: {alias} ({qid})")
                    info["source"] = "dancedb"
                    info["qid"] = qid
                    matched = True
                    break
            if matched:
                break

        if matched:
            continue

        for name, v in folketshus_venues.items():
            if venue_lower in name or name in venue_lower:
                print(f"  {venue_name} -> Folketshus: {v['name']} ({v.get('qid')})")
                info["source"] = "folketshus"
                info["qid"] = v.get("qid")
                info["external_id"] = v.get("external_id")
                matched = True
                break

        if matched:
            continue

        for v in bygdegard_venues:
            title = v.get("title", "").lower()
            if venue_lower in title or title in venue_lower:
                pos = v.get("position", {})
                print(f"  {venue_name} -> Bygdegardarna: {v['title']}")
                info["source"] = "bygdegardarna"
                info["coords"] = {"lat": pos.get("lat"), "lng": pos.get("lng")}
                info["external_id"] = v["meta"].get("permalink", "")
                matched = True
                break

    venues_to_create = {n: i for n, i in venues_needed.items() if not i.get("qid") and not i.get("source") == "dancedb"}
    print(f"\n{len(venues_to_create)} venues need to be created in DanceDB")

    if not venues_to_create:
        print("All venues resolved!")
        return

    for venue_name, info in venues_to_create.items():
        print(f"\n--- {venue_name} ---")
        source = info.get("source", "unknown")
        print(f"Source: {source}")

        coords = info.get("coords")
        if not coords:
            gmaps = f'https://www.google.com/search?q={urllib.parse.quote(venue_name, safe="")}'
            print(f"Google: {gmaps}")

        try:
            confirm = questionary.select(
                f"Create venue '{venue_name}' in DanceDB?", choices=["Yes (Recommended)", "No", "Abort"]
            ).ask()
        except Exception:
            print("Non-interactive mode - skipping creation")
            continue

        if confirm == "No":
            print("Skipping...")
            continue
        elif confirm == "Abort":
            print("Aborting...")
            sys.exit(0)
            continue

        if not coords:
            print("Enter coordinates (lat, lng) or press Enter to skip:")
            try:
                coords_input = input("> ").strip()
                if coords_input:
                    coords = parse_coords(coords_input)
            except Exception:
                print("Invalid format, skipping")
                continue

        if not coords:
            print("No coordinates - skipping")
            continue

        external_ids = {}
        if info.get("external_id"):
            external_ids["P44"] = info["external_id"]

        if dry_run:
            print(f"[DRY RUN] Would create: {venue_name} at {coords}")
            if external_ids:
                print(f"  External IDs: {external_ids}")
            continue

        db_client = DancedbClient()
        qid = create_venue(venue_name, coords["lat"], coords["lng"], external_ids=external_ids, client=db_client)
        if qid:
            print(f"Created: https://dance.wikibase.cloud/wiki/Item:{qid}")
            info["qid"] = qid
            info["source"] = "created"
        else:
            print("Failed to create venue")

    print("\nDone!")


def ensure_artists(date_str: str | None = None, dry_run: bool = False) -> None:
    """Ensure danslogen artists exist in DanceDB before uploading events."""
    from datetime import datetime

    from rapidfuzz import process as fuzz_process

    date_str = date_str or date.today().strftime("%Y-%m-%d")
    datetime.strptime(date_str, "%Y-%m-%d").strftime("%B").lower()
    print(f"\n=== Ensuring artists exist for {date_str} ===")

    dansevents_file = config.danslogen_dir / "artists" / f"{date_str}.json"
    if not dansevents_file.exists():
        print(f"Error: danslogen data not found: {dansevents_file}")
        return

    client = DancedbClient()
    existing_artists = client.fetch_artists_from_dancedb()
    existing_labels = {a.get("label", "").lower(): a for a in existing_artists if a.get("label")}
    print(f"Found {len(existing_artists)} artists in DanceDB")

    events = json.loads(dansevents_file.read_text())
    artists_needed = set(e.get("artist_name") or e.get("band") for e in events if e.get("artist_name") or e.get("band"))
    print(f"Need artists for {len(artists_needed)} unique artists")

    new_artists = []
    matched = 0
    for artist_name in artists_needed:
        if not artist_name:
            continue
        artist_lower = artist_name.lower()
        if artist_lower in existing_labels:
            matched += 1
            continue
        alias_match = False
        for existing in existing_artists:
            aliases = existing.get("aliases", [])
            for alias in aliases:
                if fuzz_process.extractOne(artist_lower, [alias], score_cutoff=80):
                    alias_match = True
                    break
            if alias_match:
                break
        if alias_match:
            matched += 1
            continue
        fuzzy = fuzz_process.extractOne(artist_lower, list(existing_labels.keys()), score_cutoff=80)
        if fuzzy:
            logger.info(f"Fuzzy matched '{artist_name}' to '{fuzzy[0]}' ({fuzzy[1]}%)")
            matched += 1
            continue
        new_artists.append(artist_name)

    print(f"Matched: {matched}")
    print(f"Need to create: {len(new_artists)}")

    if not new_artists:
        print("All artists exist in DanceDB!")
        return

    print(f"\nMissing artists: {new_artists[:20]}...")
    if len(new_artists) > 20:
        print(f"  ... and {len(new_artists) - 20} more")

    if dry_run:
        for artist_name in new_artists:
            print(f"[DRY RUN] Would create: {artist_name}")
        return

    for artist_name in new_artists[:10]:
        print(f"\n--- Creating artist: {artist_name} ---")
        print("Enter spelplan_id or press Enter to skip:")
        spelplan_id = input("> ").strip()

        if not spelplan_id:
            print("Skipping artist creation")
            continue

        try:
            qid = client.get_or_create_band(artist_name, spelplan_id=spelplan_id)
            if qid:
                print(f"Created: https://dance.wikibase.cloud/wiki/Item:{qid}")
                existing_labels[artist_name.lower()] = {"qid": qid, "label": artist_name}
            else:
                print("Failed to create artist")
        except Exception as e:
            print(f"Error creating artist: {e}")

    print("\nArtist matching done.")
