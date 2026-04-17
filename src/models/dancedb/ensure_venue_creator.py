"""Venue creation logic for ensure_venues."""
import logging
import urllib.parse
from pathlib import Path
from typing import Any

import questionary

import config
from src.models.dancedb.client import DancedbClient
from src.utils.fuzzy import normalize_for_fuzzy
from src.utils.geodb import get_ship_coordinates
from src.utils.coords import parse_coords
from src.utils.google_maps import GoogleMaps

logger = logging.getLogger(__name__)


def create_venue(venue_name: str, lat: float, lng: float, external_ids: dict | None = None, client=None) -> str | None:
    """Create a new venue in DanceDB."""
    if client is None:
        client = DancedbClient()
    return client.create_venue(venue_name=venue_name, latitude=lat, longitude=lng, external_ids=external_ids)


def prompt_for_coords(venue_name: str, folketshus_match: dict | None = None) -> dict | None:
    """Prompt for coordinates, optionally using folketshus match."""
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
            import sys
            sys.exit(0)
    
    if not coords:
        print("Enter coordinates (lat, lng) or press Enter to skip:")
        coords_input = input("> ").strip()
        if coords_input:
            parsed = parse_coords(coords_input)
            if parsed:
                coords = parsed
            else:
                print("Invalid format, skipping")
    
    if not coords:
        ship_coords = get_ship_coordinates(venue_name)
        if ship_coords:
            coords = ship_coords
            logger.info(f"Matched '{venue_name}' to ship pattern, using default coordinates: {coords['lat']}, {coords['lng']}")
            print(f"Using default ship coordinates: {coords['lat']}, {coords['lng']}")
    
    return coords


def find_local_match(coords: dict, folketshus_venues: dict) -> dict | None:
    """Search for local (folketshus/bygdegardarna) coordinate match."""
    from src.utils.distance import haversine_distance
    
    for fh_name, fh_venue in folketshus_venues.items():
        fh_lat = fh_venue.get("lat")
        fh_lng = fh_venue.get("lng")
        if fh_lat and fh_lng:
            dist = haversine_distance(coords["lat"], coords["lng"], fh_lat, fh_lng)
            if dist <= config.COORD_MATCH_THRESHOLD_KM:
                logger.info(f"Coord match: '{fh_name}' matches folketshus at {dist:.3f}km")
                return fh_venue
    return None


def find_dancedb_match(client: DancedbClient, coords: dict) -> list[dict]:
    """Search for DanceDB venue by coordinates."""
    threshold = config.COORD_MATCH_THRESHOLD_KM
    return client.find_venues_by_coordinates(coords["lat"], coords["lng"], threshold_km=threshold)


def prompt_for_dancedb_match(venue_name: str, coords: dict, matches: list[dict]) -> str | None:
    """Prompt user to select a DanceDB venue match."""
    if not matches:
        return None
    
    print(f"\nFound {len(matches)} DanceDB venue(s) within {config.COORD_MATCH_THRESHOLD_KM}km:")
    choices = [f"{m['label']} ({m['distance_km']*1000:.0f}m, {m['qid']})" for m in matches]
    choices.extend(["Create new venue (skip DanceDB)", "Abort"])
    
    selected = questionary.select(
        f"Match '{venue_name}' to existing DanceDB venue?",
        choices=choices,
    ).ask()
    
    if selected and "Create new venue" not in selected and "Abort" not in selected:
        for m in matches:
            if selected.startswith(m["label"]):
                return m["qid"]
    elif "Abort" in selected:
        print("Aborting...")
        import sys
        sys.exit(0)
    return None


def create_new_venue(venue_name: str, coords: dict, folketshus_match: dict | None, db_client, date_str: str) -> str | None:
    """Create a new venue with the given coordinates."""
    from src.models.dancedb.ensure_venue_matcher import save_venue_mapping
    
    # Check if already matched via folketshus with QID
    if folketshus_match and folketshus_match.get("qid"):
        existing_qid = folketshus_match["qid"]
        logger.info(f"Skipping creation: using existing folketshus venue Q{existing_qid}")
        print(f"Using existing venue: Q{existing_qid}")
        save_venue_mapping(venue_name, existing_qid, coords["lat"], coords["lng"], date_str, source="folketshus", external_id=folketshus_match.get("external_id"))
        return existing_qid
    
    # Prepare external IDs
    external_ids = None
    if folketshus_match:
        external_ids = {"P44": folketshus_match["external_id"]}
    
    # Create venue
    qid = create_venue(venue_name, coords["lat"], coords["lng"], external_ids=external_ids, client=db_client)
    if qid:
        print(f"Created: https://dance.wikibase.cloud/wiki/Item:{qid}")
        save_venue_mapping(venue_name, qid, coords["lat"], coords["lng"], date_str)
    else:
        print("Failed to create venue")
    
    return qid


def create_venue_interactive(venue_name: str, folketshus_venues: dict, folketshus_names: list, db_client, date_str: str) -> bool:
    """Interactive venue creation flow. Returns True if venue was created/matched."""
    import sys
    
    print(f"\n--- Creating venue: {venue_name} ---")
    
    # Try to find folketshus match
    folketshus_match = None
    if folketshus_names:
        from rapidfuzz import fuzz, process as fuzz_process
        normalized = {normalize_for_fuzzy(n, config.FUZZY_REMOVE_TERMS_FOLKETSHUS): n for n in folketshus_names}
        fuzzy = fuzz_process.extractOne(
            normalize_for_fuzzy(venue_name.lower(), config.FUZZY_REMOVE_TERMS_FOLKETSHUS),
            normalized.keys(),
            scorer=fuzz.token_set_ratio,
            score_cutoff=config.FUZZY_THRESHOLD_VENUE_FOLKETSHUS
        )
        if fuzzy:
            folkets_original = normalized[fuzzy[0]]
            folketshus_match = folketshus_venues[fuzzy[0]]
            print(f"Found in folketshus: {fuzzy[0]} ({fuzzy[1]}, external_id: {folketshus_match.get('external_id', 'N/A')})")
    
    # Show search links
    gmaps = f'https://www.google.com/maps/search/{urllib.parse.quote(venue_name, safe="")}'
    osm = f'https://www.openstreetmap.org/search?query={urllib.parse.quote(venue_name, safe="")}'
    print(f"Google: {gmaps}")
    
    # Get coordinates
    coords = prompt_for_coords(venue_name, folketshus_match)
    if not coords:
        print("Skipping venue creation (no coordinates)")
        return False
    
    # Search local geodb
    logger.info(f"Searching local geodb for venues near ({coords['lat']}, {coords['lng']}) within {config.COORD_MATCH_THRESHOLD_KM}km...")
    geodb_matches = geodb.find_nearby(coords["lat"], coords["lng"], threshold_km=config.COORD_MATCH_THRESHOLD_KM, limit=10)
    logger.info(f"Local geodb search returned {len(geodb_matches)} matches")
    
    if geodb_matches:
        print(f"\nFound {len(geodb_matches)} local match(es) by coordinates:")
        for m in geodb_matches:
            src = m["source"]
            ext = m.get("external_id", "")
            qid_info = f", Q{m['qid']}" if m.get("qid") else ""
            print(f"  - {m['name']} ({src}, {m['distance_km']*1000:.0f}m{qid_info})")
        
        choices = [f"{m['name']} ({m['source']}, {m['distance_km']*1000:.0f}m)" for m in geodb_matches]
        choices.extend(["Create new venue (skip matches)", "Abort"])
        
        selected = questionary.select(f"Match '{venue_name}' to local venue?", choices=choices).ask()
        
        if selected and "Create new venue" not in selected and "Abort" not in selected:
            for m in geodb_matches:
                if selected.startswith(m["name"]):
                    matched_qid = m.get("qid")
                    matched_source = m["source"]
                    matched_external_id = m.get("external_id", "")
                    
                    if matched_qid:
                        logger.info(f"Matched '{venue_name}' to {matched_source} venue {matched_qid} by coordinates")
                        print(f"Using existing {matched_source} venue: {m['name']} (Q{matched_qid})")
                        from src.models.dancedb.ensure_venue_matcher import save_venue_mapping
                        save_venue_mapping(venue_name, matched_qid, coords["lat"], coords["lng"], date_str, source=matched_source, external_id=matched_external_id)
                        return True
                    else:
                        print(f"Using {matched_source} coordinates: {m['lat']}, {m['lng']}")
                        if matched_source == "folketshus":
                            folketshus_match = {"lat": m["lat"], "lng": m["lng"], "external_id": matched_external_id}
                    break
            return True
        elif "Abort" in selected:
            print("Aborting...")
            sys.exit(0)
        elif "Create new venue" in selected:
            pass
    else:
        logger.info("No local matches found, falling through to DanceDB")
    
    # Check local folketshus coordinate match
    local_folkets = find_local_match(coords, folketshus_venues)
    if local_folkets:
        folketshus_match = local_folkets
    
    # Search DanceDB
    if db_client:
        dancedb_matches = find_dancedb_match(db_client, coords)
        if dancedb_matches:
            existing_qid = prompt_for_dancedb_match(venue_name, coords, dancedb_matches)
            if existing_qid:
                from src.models.dancedb.ensure_venue_matcher import save_venue_mapping
                save_venue_mapping(venue_name, existing_qid, coords["lat"], coords["lng"], date_str, source="dancedb")
                return True
    
    # Create new venue
    qid = create_new_venue(venue_name, coords, folketshus_match, db_client, date_str)
    return qid is not None