"""Ensure venues exist in DanceDB."""
import json
import logging
import math
import sys
import urllib.parse
from datetime import date

import questionary
from rapidfuzz import fuzz, process as fuzz_process
from wikibaseintegrator.wbi_config import config as wbi_config

import config
from src.models.dancedb.client import DancedbClient
from src.utils.fuzzy import normalize_for_fuzzy
from src.utils.google_maps import GoogleMaps
from src.utils.qid import Qid

logger = logging.getLogger(__name__)


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two points in km."""
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


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


def ensure_venues(date_str: str | None = None) -> None:
    """Ensure danslogen venues exist in DanceDB before uploading events."""
    require_tty()

    date_str = date_str or date.today().strftime("%Y-%m-%d")
    month_name = date.strptime(date_str, "%Y-%m-%d").strftime("%B").lower()
    print(f"\n=== Ensuring venues exist for {date_str} ===")

    dansevents_file = config.danslogen_dir / "events" / f"{date_str}-{month_name}.json"
    if not dansevents_file.exists():
        print(f"Error: danslogen data not found: {dansevents_file}")
        return

    bygdegardarna_dir = config.data_dir / "bygdegardarna" / "enriched"
    bygdegardarna_venues = {}
    bygdegardarna_names = []
    bygdegardarna_cities = {}
    if bygdegardarna_dir.exists():
        bygdegardarna_files = sorted(bygdegardarna_dir.glob("*.json"), reverse=True)
        if bygdegardarna_files:
            bygdegardarna_file = bygdegardarna_files[0]
            bygdegardarna_data = json.loads(bygdegardarna_file.read_text())
            bygdegardarna_venues = {v["title"].lower(): v for v in bygdegardarna_data if v.get("qid")}
            bygdegardarna_names = list(bygdegardarna_venues.keys())
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

        matched_addr = False
        if bygdegardarna_addresses and len(venue_lower) >= 5:
            fuzzy_addr = fuzz_process.extractOne(
                venue_lower,
                list(bygdegardarna_addresses.keys()),
                scorer=fuzz.token_sort_ratio,
                score_cutoff=config.FUZZY_THRESHOLD_VENUE_BYGDEGARDARNA + 2
            )
            if fuzzy_addr:
                addr_data = bygdegardarna_addresses[fuzzy_addr[0]]
                gmaps_url = addr_data.get("gmaps_url", "")
                permalink = addr_data.get("permalink", "")
                url_info = f"bygdegardarna.se: {permalink}" if permalink else f"Google: {gmaps_url}"
                confirm = questionary.select(
                    f"Match '{venue_name}' to bygdegardarna address '{addr_data.get('address')}' ({fuzzy_addr[1]:.1f}%)?\n→ {url_info}",
                    choices=["Yes (Recommended)", "No", "Abort"],
                ).ask()
                if confirm == "No":
                    pass
                elif confirm == "Abort":
                    print("Aborting...")
                    sys.exit(0)
                else:
                    existing_venues[venue_lower] = {
                        "qid": addr_data.get("qid", ""),
                        "lat": addr_data.get("lat"),
                        "lng": addr_data.get("lng"),
                        "aliases": [],
                    }
                    logger.info(f"Matched '{venue_name}' to bygdegardarna address '{fuzzy_addr[0]}' ({fuzzy_addr[1]:.1f}%)")
                    matched += 1
                    matched_addr = True
                    
                    venue_mapping_file = config.data_dir / "dancedb" / "venue_mappings.jsonl"
                    venue_mapping_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(venue_mapping_file, "a") as f:
                        f.write(json.dumps({"venue_name": venue_name, "qid": addr_data.get("qid", ""), "lat": addr_data.get("lat"), "lng": addr_data.get("lng"), "gmaps_url": gmaps_url, "permalink": permalink, "created_at": date_str}) + "\n")

        if not matched_addr:
            matched_city = False
            if bygdegardarna_cities and len(venue_lower) >= 5:
                fuzzy_city = fuzz_process.extractOne(
                    venue_lower,
                    list(bygdegardarna_cities.keys()),
                    scorer=fuzz.token_sort_ratio,
                    score_cutoff=config.FUZZY_THRESHOLD_VENUE_BYGDEGARDARNA + 2
                )
                if fuzzy_city:
                    city_venue = bygdegardarna_cities[fuzzy_city[0]]
                    city_display = fuzzy_city[0].title() if fuzzy_city[0].islower() else fuzzy_city[0]
                    gmaps_url = city_venue.get("gmaps_url", "")
                    meta = city_venue.get("meta", {})
                    permalink = meta.get("permalink", "") or city_venue.get("permalink", "")
                    url_info = f"bygdegardarna.se: {permalink}" if permalink else f"Google: {gmaps_url}"
                    confirm = questionary.select(
                        f"Match '{venue_name}' to bygdegardarna city '{city_display}' ({fuzzy_city[1]:.1f}%)?\n→ {url_info}",
                        choices=["Yes (Recommended)", "No", "Abort"],
                    ).ask()
                    if confirm == "No":
                        pass
                    elif confirm == "Abort":
                        print("Aborting...")
                        sys.exit(0)
                    else:
                        existing_venues[venue_lower] = {
                            "qid": city_venue.get("qid", ""),
                            "lat": city_venue.get("lat"),
                            "lng": city_venue.get("lng"),
                            "aliases": [],
                        }
                        logger.info(f"Matched '{venue_name}' to bygdegardarna city '{fuzzy_city[0]}' ({fuzzy_city[1]:.1f}%)")
                        matched_city = True
                        matched += 1

                        venue_mapping_file = config.data_dir / "dancedb" / "venue_mappings.jsonl"
                        venue_mapping_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(venue_mapping_file, "a") as f:
                            f.write(json.dumps({"venue_name": venue_name, "qid": city_venue.get("qid", ""), "lat": city_venue.get("lat"), "lng": city_venue.get("lng"), "gmaps_url": gmaps_url, "permalink": city_venue.get("permalink", ""), "created_at": date_str}) + "\n")

            if not matched_addr and not matched_city:
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

        coords = None
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
                from src.utils.coords import parse_coords
                coords = parse_coords(coords_input)
                if not coords:
                    print("Invalid format, skipping")

        if coords and not folketshus_match and folketshus_venues:
            for fh_name, fh_venue in folketshus_venues.items():
                fh_lat = fh_venue.get("lat")
                fh_lng = fh_venue.get("lng")
                if fh_lat and fh_lng:
                    dist = haversine_distance(coords["lat"], coords["lng"], fh_lat, fh_lng)
                    if dist <= config.COORD_MATCH_THRESHOLD_KM:
                        folketshus_match = fh_venue
                        logger.info(f"Coord match: '{venue_name}' matches folketshus '{fh_name}' at {dist:.3f}km")
                        print(f"Matched by coordinates: {fh_name} ({dist:.3f}km, external_id: {fh_venue['external_id']}, qid: {fh_venue.get('qid', 'N/A')})")
                        break

        if not coords:
            print("Skipping venue creation (no coordinates)")
            continue

        if folketshus_match and folketshus_match.get("qid"):
            existing_qid = folketshus_match["qid"]
            logger.info(f"Skipping creation: using existing folketshus venue Q{existing_qid}")
            print(f"Using existing venue: Q{existing_qid}")
            existing_venues[venue_name.lower()] = {"qid": existing_qid, "lat": coords["lat"], "lng": coords["lng"]}
            venue_mapping_file = config.data_dir / "dancedb" / "venue_mappings.jsonl"
            venue_mapping_file.parent.mkdir(parents=True, exist_ok=True)
            with open(venue_mapping_file, "a") as f:
                f.write(json.dumps({
                    "venue_name": venue_name, "qid": existing_qid, "lat": coords["lat"], "lng": coords["lng"],
                    "source": "folketshus", "external_id": folketshus_match.get("external_id"), "created_at": date_str
                }) + "\n")
            print(f"  -> Saved mapping to {venue_mapping_file.name}")
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
