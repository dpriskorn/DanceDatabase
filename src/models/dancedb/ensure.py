"""Ensure venues exist in DanceDB.

This module provides venue matching and creation functionality.
Core coordinate-based matching has been moved to ensure_coords.py.
"""
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
from src.models.dancedb.ensure_coords import find_dancedb_venues_by_coords
from src.utils.distance import haversine_distance
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

    folketshus_dir = config.data_dir / "folketshus"
    folketshus_venues = {}
    folketshus_names = []
    for subdir in ["enriched", "unmatched"]:
        subdir_path = folketshus_dir / subdir
        if subdir_path.exists():
            folketshus_files = sorted(subdir_path.glob("*.json"), reverse=True)
            if folketshus_files:
                folketshus_file = folketshus_files[0]
                folketshus_data = json.loads(folketshus_file.read_text())
                for v in folketshus_data:
                    v["source_dir"] = subdir
                    address = v.get("address", "")
                    lat = v.get("lat")
                    lng = v.get("lng")
                    gmaps = GoogleMaps(address=address, lat=lat, lng=lng)
                    v["gmaps_url"] = gmaps.url
                    name_lower = v["name"].lower()
                    if name_lower not in folketshus_venues:
                        folketshus_venues[name_lower] = v
                print(f"Loaded {len(folketshus_data)} folketshus venues from {subdir}/")
    folketshus_names = list(folketshus_venues.keys())
    print(f"Loaded {len(folketshus_venues)} total folketshus venues for auto-match")

    from wikibaseintegrator.wbi_helpers import execute_sparql_query

    wbi_config["User-Agent"] = "DanceDB/1.0 (User:So9q)"

    sparql = """
    PREFIX dd: <https://dance.wikibase.cloud/entity/>
    PREFIX ddt: <https://dance.wikibase.cloud/prop/direct/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

    SELECT ?item ?itemLabel (GROUP_CONCAT(?svAlias; SEPARATOR = "|") AS ?aliasStr) ?geo WHERE {
      ?item ddt:P1 dd:Q20 .
      OPTIONAL { ?item rdfs:label ?itemLabel FILTER(LANG(?itemLabel) = "sv") }
      OPTIONAL { ?item skos:altLabel ?svAlias FILTER(LANG(?svAlias) = "sv") }
      OPTIONAL { ?item ddt:P4 ?geo }
    }
    GROUP BY ?item ?itemLabel ?geo
    ORDER BY ?itemLabel
    """
    results = execute_sparql_query(query=sparql)
    existing_venues = {}
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
        label_lower = label.lower()
        if label_lower not in existing_venues:
            existing_venues[label_lower] = {"qid": qid, "lat": lat, "lng": lng, "aliases": aliases}
        elif aliases:
            existing_venues[label_lower].setdefault("aliases", []).extend(aliases)

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

    venues_list = list(venues_needed)
    total_venues = len(venues_list)
    step1_done = False
    step2_done = False

    new_venues = []
    matched = 0
    matched_auto = 0
    for idx, venue_name in enumerate(venues_list):
        remaining = total_venues - idx
        print(f"=== [{idx + 1}/{total_venues}] Remaining: {remaining} ===")
        venue_lower = venue_name.lower()
        existing = existing_venues.get(venue_lower)
        if not existing:
            for key, v in existing_venues.items():
                if venue_lower in v.get("aliases", []):
                    existing = v
                    venue_lower = key
                    break
        if existing:
            matched += 1
            matched_auto += 1
            venue_mapping_file = config.data_dir / "dancedb" / "venue_mappings.jsonl"
            venue_mapping_file.parent.mkdir(parents=True, exist_ok=True)
            gmaps = GoogleMaps(lat=existing.get("lat"), lng=existing.get("lng"))
            with open(venue_mapping_file, "a") as f:
                f.write(json.dumps({"venue_name": venue_name, "qid": existing["qid"], "lat": existing.get("lat"), "lng": existing.get("lng"), "gmaps_url": gmaps.url, "created_at": date_str}) + "\n")
            print(f"Auto-matched: '{venue_name}' → {venue_lower}")
            continue

        if not step1_done:
            logger.info("Step 2: Fuzzy matching against bygdegardarna (with prompt)")
            step1_done = True

        if bygdegardarna_names:
            if not step2_done:
                logger.info(f"Step 3: Fuzzy matching against {len(bygdegardarna_names)} bygdegardarna venues (threshold {config.FUZZY_THRESHOLD_VENUE_BYGDEGARDARNA}%)...")
                step2_done = True
            
            bygdegardarna_normalized = {normalize_for_fuzzy(n, config.FUZZY_REMOVE_TERMS_BYGDEGARDARNA): n for n in bygdegardarna_names}
            fuzzy_byg = fuzz_process.extractOne(
                normalize_for_fuzzy(venue_lower, config.FUZZY_REMOVE_TERMS_BYGDEGARDARNA),
                bygdegardarna_normalized.keys(),
                scorer=fuzz.token_set_ratio,
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

        folkets_match = False
        if folketshus_names:
            folketshus_normalized = {normalize_for_fuzzy(n, config.FUZZY_REMOVE_TERMS_FOLKETSHUS): n for n in folketshus_names}
            fuzzy_folkets = fuzz_process.extractOne(
                normalize_for_fuzzy(venue_lower, config.FUZZY_REMOVE_TERMS_FOLKETSHUS),
                folketshus_normalized.keys(),
                scorer=fuzz.token_set_ratio,
                score_cutoff=95
            )
            if fuzzy_folkets:
                folkets_original = folketshus_normalized[fuzzy_folkets[0]]
                folkets_match = folketshus_venues[folkets_original]
                gmaps_url = folkets_match.get("gmaps_url", "")
                if fuzzy_folkets[1] >= config.FUZZY_AUTOMATCH_THRESHOLD_VENUE_FOLKETSHUS:
                    matched += 1
                    matched_auto += 1
                    existing_venues[venue_lower] = {
                        "qid": folkets_match.get("qid", ""),
                        "lat": folkets_match.get("lat"),
                        "lng": folkets_match.get("lng"),
                        "aliases": [],
                    }
                    venue_mapping_file = config.data_dir / "dancedb" / "venue_mappings.jsonl"
                    venue_mapping_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(venue_mapping_file, "a") as f:
                        f.write(json.dumps({"venue_name": venue_name, "qid": folkets_match.get("qid", ""), "lat": folkets_match.get("lat"), "lng": folkets_match.get("lng"), "gmaps_url": gmaps_url, "created_at": date_str}) + "\n")
                    print(f"Auto-matched: '{venue_name}' → folketshus '{folkets_original}' ({fuzzy_folkets[1]:.1f}%)")
                    continue
                confirm = questionary.select(
                    f"Match '{venue_name}' to folketshus '{folkets_original}' ({fuzzy_folkets[1]:.1f}%)?\n→ {gmaps_url}",
                    choices=["Yes (Recommended)", "No", "Abort"],
                ).ask()
                if confirm == "No":
                    pass
                elif confirm == "Abort":
                    print("Aborting...")
                    sys.exit(0)
                else:
                    matched += 1
                    existing_venues[venue_lower] = {
                        "qid": folkets_match.get("qid", ""),
                        "lat": folkets_match.get("lat"),
                        "lng": folkets_match.get("lng"),
                        "aliases": [],
                    }
                    venue_mapping_file = config.data_dir / "dancedb" / "venue_mappings.jsonl"
                    venue_mapping_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(venue_mapping_file, "a") as f:
                        f.write(json.dumps({"venue_name": venue_name, "qid": folkets_match.get("qid", ""), "lat": folkets_match.get("lat"), "lng": folkets_match.get("lng"), "gmaps_url": gmaps_url, "created_at": date_str}) + "\n")
                    continue

        matched_addr = False
        if bygdegardarna_addresses and len(venue_lower) >= 5:
            fuzzy_addr = fuzz_process.extractOne(
                venue_lower,
                list(bygdegardarna_addresses.keys()),
                scorer=fuzz.token_set_ratio,
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
                    scorer=fuzz.token_set_ratio,
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

    print(f"Auto-matched (exact): {matched_auto}")
    print(f"Matched (with prompt): {matched}")
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
                scorer=fuzz.token_set_ratio,
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

        if not coords:
            from src.utils.geodb import get_ship_coordinates
            ship_coords = get_ship_coordinates(venue_name)
            if ship_coords:
                coords = ship_coords
                logger.info(f"Matched '{venue_name}' to ship pattern, using default coordinates: {coords['lat']}, {coords['lng']}")
                print(f"Using default ship coordinates: {coords['lat']}, {coords['lng']}")

        if coords:
            from src.utils import geodb
            logger.info(f"Searching local geodb for venues near ({coords['lat']}, {coords['lng']}) within {config.COORD_MATCH_THRESHOLD_KM}km...")
            geodb_matches = geodb.find_nearby(
                coords["lat"], coords["lng"], 
                threshold_km=config.COORD_MATCH_THRESHOLD_KM,
                limit=10
            )
            logger.info(f"Local geodb search returned {len(geodb_matches)} matches")
            if geodb_matches:
                print(f"\nFound {len(geodb_matches)} local match(es) by coordinates:")
                for m in geodb_matches:
                    src = m["source"]
                    ext = m.get("external_id", "")
                    qid_info = f", Q{m['qid']}" if m.get("qid") else ""
                    print(f"  - {m['name']} ({src}, {m['distance_km']*1000:.0f}m{ qid_info})")
                
                choices = [f"{m['name']} ({m['source']}, {m['distance_km']*1000:.0f}m)" for m in geodb_matches]
                choices.extend(["Create new venue (skip matches)", "Abort"])
                selected = questionary.select(
                    f"Match '{venue_name}' to local venue?",
                    choices=choices,
                ).ask()
                
                if selected and "Create new venue" not in selected and "Abort" not in selected:
                    for m in geodb_matches:
                        if selected.startswith(m["name"]):
                            matched_qid = m.get("qid")
                            matched_source = m["source"]
                            matched_external_id = m.get("external_id", "")
                            
                            if matched_qid:
                                logger.info(f"Matched '{venue_name}' to {matched_source} venue {matched_qid} by coordinates")
                                print(f"Using existing {matched_source} venue: {m['name']} (Q{matched_qid})")
                                existing_venues[venue_name.lower()] = {"qid": matched_qid, "lat": coords["lat"], "lng": coords["lng"], "aliases": []}
                                venue_mapping_file = config.data_dir / "dancedb" / "venue_mappings.jsonl"
                                venue_mapping_file.parent.mkdir(parents=True, exist_ok=True)
                                with open(venue_mapping_file, "a") as f:
                                    f.write(json.dumps({
                                        "venue_name": venue_name, "qid": matched_qid, "lat": coords["lat"], "lng": coords["lng"],
                                        "source": matched_source, "external_id": matched_external_id, "created_at": date_str
                                    }) + "\n")
                                print(f"  -> Saved mapping to {venue_mapping_file.name}")
                            else:
                                print(f"Using {matched_source} coordinates: {m['lat']}, {m['lng']}")
                                coords = {"lat": m["lat"], "lng": m["lng"]}
                                if matched_source == "folketshus":
                                    folketshus_match = {"lat": m["lat"], "lng": m["lng"], "external_id": matched_external_id}
                                elif matched_source == "bygdegardarna":
                                    pass
                            break
                    continue
                elif "Abort" in selected:
                    print("Aborting...")
                    sys.exit(0)
                elif "Create new venue" in selected:
                    pass
            else:
                logger.info("No local matches found, falling through to DanceDB")

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

        if coords and not folketshus_match and db_client:
            lat, lng = coords["lat"], coords["lng"]
            threshold = config.COORD_MATCH_THRESHOLD_KM
            lat_delta = threshold / 111
            lng_delta = threshold / (111 * math.cos(math.radians(lat)))
            lng_min, lng_max = lng - lng_delta, lng + lng_delta
            lat_min, lat_max = lat - lat_delta, lat + lat_delta
            debug_url = f"https://dance.wikibase.cloud/query/sparql?query=PREFIX+dd:+%3Chttps://dance.wikibase.cloud/entity/%3E+PREFIX+ddt:+%3Chttps://dance.wikibase.cloud/prop/direct/%3E+SELECT+?item+?itemLabel+?location+WHERE+%7B+SERVICE+wikibase:box+%7B+%3Fitem+ddt:P4+?location+.+bd:serviceParam+wikibase:cornerWest+%22Point({lng_min}+{lat_min})%22%5E%5Egeo:wktLiteral+.+bd:serviceParam+wikibase:cornerEast+%22Point({lng_max}+{lat_max})%22%5E%5Egeo:wktLiteral+.+%7D+%3Fitem+ddt:P1+dd:Q20+.+OPTIONAL+%7B+%3Fitem+rdfs:label+?itemLabel+FILTER(LANG(%3FitemLabel)+%3D+%22sv%22)%7D%7D"
            logger.debug(f"Searching DanceDB for venues near ({lat}, {lng}) within {threshold}km... Query: {debug_url}")
            dancedb_matches = db_client.find_venues_by_coordinates(
                lat, lng, threshold_km=threshold
            )
            if not dancedb_matches:
                logger.debug(f"No DanceDB venues found within {threshold}km of ({lat}, {lng})")
            if dancedb_matches:
                print(f"\nFound {len(dancedb_matches)} DanceDB venue(s) within {config.COORD_MATCH_THRESHOLD_KM}km:")
                choices = [f"{m['label']} ({m['distance_km']*1000:.0f}m, {m['qid']})" for m in dancedb_matches]
                choices.extend(["Create new venue (skip DanceDB)", "Abort"])
                selected = questionary.select(
                    f"Match '{venue_name}' to existing DanceDB venue?",
                    choices=choices,
                ).ask()
                if selected and "Create new venue" not in selected and "Abort" not in selected:
                    for m in dancedb_matches:
                        if selected.startswith(m["label"]):
                            existing_qid = m["qid"]
                            matched_aliases = m.get("aliases", [])
                            logger.info(f"Matched '{venue_name}' to DanceDB venue {existing_qid} by coordinates")
                            print(f"Using existing DanceDB venue: {m['label']} ({m['qid']})")
                            existing_venues[venue_name.lower()] = {"qid": existing_qid, "lat": coords["lat"], "lng": coords["lng"], "aliases": matched_aliases}
                            venue_mapping_file = config.data_dir / "dancedb" / "venue_mappings.jsonl"
                            venue_mapping_file.parent.mkdir(parents=True, exist_ok=True)
                            with open(venue_mapping_file, "a") as f:
                                f.write(json.dumps({
                                    "venue_name": venue_name, "qid": existing_qid, "lat": coords["lat"], "lng": coords["lng"],
                                    "source": "dancedb", "created_at": date_str
                                }) + "\n")
                            print(f"  -> Saved mapping to {venue_mapping_file.name}")
                            break
                    else:
                        continue
                elif "Abort" in selected:
                    print("Aborting...")
                    sys.exit(0)
                elif "Create new venue" in selected:
                    pass

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
