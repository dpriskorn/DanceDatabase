"""Venue matching logic for ensure_venues."""
import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

import questionary
from rapidfuzz import fuzz, process as fuzz_process

import config
from src.utils.fuzzy import normalize_for_fuzzy
from src.utils.google_maps import GoogleMaps
from src.utils.distance import haversine_distance
from src.utils import geodb

logger = logging.getLogger(__name__)


def require_tty():
    """Ensure running in interactive terminal."""
    import sys
    if not sys.stdin.isatty():
        raise RuntimeError("This operation requires an interactive terminal.")
    return True


def save_venue_mapping(venue_name: str, qid: str, lat: float | None, lng: float, date_str: str, **extra) -> None:
    """Save a venue mapping to the jsonl file."""
    venue_mapping_file = config.data_dir / "dancedb" / "venue_mappings.jsonl"
    venue_mapping_file.parent.mkdir(parents=True, exist_ok=True)
    data = {"venue_name": venue_name, "qid": qid, "lat": lat, "lng": lng, "created_at": date_str, **extra}
    with open(venue_mapping_file, "a") as f:
        f.write(json.dumps(data) + "\n")


def match_exact(venue_lower: str, existing_venues: dict) -> dict | None:
    """Check for exact label match or alias match."""
    existing = existing_venues.get(venue_lower)
    if existing:
        return venue_lower
    for key, v in existing_venues.items():
        if venue_lower in v.get("aliases", []):
            return key
    return None


def match_fuzzy(venue_lower: str, candidates: dict, threshold: float, remove_terms: list) -> tuple[str, Any] | None:
    """Fuzzy match against candidates."""
    normalized = {normalize_for_fuzzy(n, remove_terms): n for n in candidates.keys()}
    result = fuzz_process.extractOne(
        normalize_for_fuzzy(venue_lower, remove_terms),
        normalized.keys(),
        scorer=fuzz.token_set_ratio,
        score_cutoff=threshold
    )
    if result:
        original = normalized[result[0]]
        return original, candidates[original]
    return None


def match_by_coords(venue_lat: float, venue_lng: float, candidate_coords: dict, threshold_km: float) -> tuple | None:
    """Match by coordinate proximity."""
    for qid, (lat2, lng2) in candidate_coords.items():
        dist = haversine_distance(venue_lat, venue_lng, lat2, lng2)
        if dist <= threshold_km:
            return qid, dist
    return None


def prompt_match(venue_name: str, matched_name: str, score: float, gmaps_url: str, source: str) -> bool:
    """Prompt user to confirm a match. Returns True if confirmed."""
    confirm = questionary.select(
        f"Match '{venue_name}' to {source} '{matched_name}' ({score:.1f}%)?\n→ {gmaps_url}",
        choices=["Yes (Recommended)", "No", "Abort"],
    ).ask()
    if confirm == "No":
        return False
    elif confirm == "Abort":
        import sys
        print("Aborting...")
        sys.exit(0)
    return True


def match_venue(
    venue_name: str,
    existing_venues: dict,
    bygdegardarna_venues: dict,
    bygdegardarna_names: list,
    bygdegardarna_cities: dict,
    bygdegardarna_addresses: dict,
    folketshus_venues: dict,
    folketshus_names: list,
    date_str: str,
) -> tuple[str | None, dict | None]:
    """Main venue matching logic. Returns (matched_name, match_data) or (None, None)."""
    require_tty()
    venue_lower = venue_name.lower()
    
    # Step 1: Exact match in existing venues
    match_key = match_exact(venue_lower, existing_venues)
    if match_key:
        existing = existing_venues[match_key]
        save_venue_mapping(venue_name, existing["qid"], existing.get("lat"), existing.get("lng"), date_str)
        gmaps = GoogleMaps(lat=existing.get("lat"), lng=existing.get("lng"))
        print(f"Auto-matched: '{venue_name}' → {match_key}")
        return match_key, existing
    
    # Step 2: Fuzzy match against bygdegardarna
    if bygdegardarna_names:
        result = match_fuzzy(venue_lower, bygdegardarna_venues, config.FUZZY_THRESHOLD_VENUE_BYGDEGARDARNA, config.FUZZY_REMOVE_TERMS_BYGDEGARDARNA)
        if result:
            byg_original, byg_match = result
            existing_venues[venue_lower] = {"qid": byg_match["qid"], "lat": byg_match.get("lat"), "lng": byg_match.get("lng"), "aliases": []}
            logger.info(f"Matched '{venue_name}' to bygdegardarna '{byg_original}'")
            save_venue_mapping(venue_name, byg_match.get("qid", ""), byg_match.get("lat"), byg_match.get("lng"), date_str, gmaps_url=byg_match.get("gmaps_url", ""))
            return byg_original, byg_match
    
    # Step 3: Fuzzy match against folketshus
    if folketshus_names:
        result = match_fuzzy(venue_lower, folketshus_venues, config.FUZZY_THRESHOLD_VENUE_FOLKETSHUS, config.FUZZY_REMOVE_TERMS_FOLKETSHUS)
        if result:
            folkets_original, folkets_match = result
            gmaps_url = folkets_match.get("gmaps_url", "")
            
            if fuzz_process.extractOne(venue_lower, [folkets_original], scorer=fuzz.token_set_ratio, score_cutoff=config.FUZZY_AUTOMATCH_THRESHOLD_VENUE_FOLKETSHUS):
                existing_venues[venue_lower] = {"qid": folkets_match.get("qid", ""), "lat": folkets_match.get("lat"), "lng": folkets_match.get("lng"), "aliases": []}
                save_venue_mapping(venue_name, folkets_match.get("qid", ""), folkets_match.get("lat"), folkets_match.get("lng"), date_str, gmaps_url=gmaps_url)
                print(f"Auto-matched: '{venue_name}' → folketshus '{folkets_original}'")
                return folkets_original, folkets_match
            
            if prompt_match(venue_name, folkets_original, 95.0, gmaps_url, "folketshus"):
                existing_venues[venue_lower] = {"qid": folkets_match.get("qid", ""), "lat": folkets_match.get("lat"), "lng": folkets_match.get("lng"), "aliases": []}
                save_venue_mapping(venue_name, folkets_match.get("qid", ""), folkets_match.get("lat"), folkets_match.get("lng"), date_str, gmaps_url=gmaps_url)
                return folkets_original, folkets_match
    
    # Step 4: Address matching
    if bygdegardarna_addresses and len(venue_lower) >= 5:
        result = fuzz_process.extractOne(venue_lower, list(bygdegardarna_addresses.keys()), scorer=fuzz.token_set_ratio, score_cutoff=config.FUZZY_THRESHOLD_VENUE_BYGDEGARDARNA + 2)
        if result:
            addr_data = bygdegardarna_addresses[result[0]]
            gmaps_url = addr_data.get("gmaps_url", "")
            permalink = addr_data.get("permalink", "")
            url_info = f"bygdegardarna.se: {permalink}" if permalink else f"Google: {gmaps_url}"
            
            if prompt_match(venue_name, addr_data.get("address", ""), result[1], url_info, "bygdegardarna address"):
                existing_venues[venue_lower] = {"qid": addr_data.get("qid", ""), "lat": addr_data.get("lat"), "lng": addr_data.get("lng"), "aliases": []}
                logger.info(f"Matched '{venue_name}' to bygdegardarna address '{result[0]}'")
                save_venue_mapping(venue_name, addr_data.get("qid", ""), addr_data.get("lat"), addr_data.get("lng"), date_str, gmaps_url=gmaps_url, permalink=permalink)
                return result[0], addr_data
    
    # Step 5: City matching
    if bygdegardarna_cities and len(venue_lower) >= 5:
        result = fuzz_process.extractOne(venue_lower, list(bygdegardarna_cities.keys()), scorer=fuzz.token_set_ratio, score_cutoff=config.FUZZY_THRESHOLD_VENUE_BYGDEGARDARNA + 2)
        if result:
            city_venue = bygdegardarna_cities[result[0]]
            gmaps_url = city_venue.get("gmaps_url", "")
            meta = city_venue.get("meta", {})
            permalink = meta.get("permalink", "") or city_venue.get("permalink", "")
            url_info = f"bygdegardarna.se: {permalink}" if permalink else f"Google: {gmaps_url}"
            city_display = result[0].title() if result[0].islower() else result[0]
            
            if prompt_match(venue_name, city_display, result[1], url_info, "bygdegardarna city"):
                existing_venues[venue_lower] = {"qid": city_venue.get("qid", ""), "lat": city_venue.get("lat"), "lng": city_venue.get("lng"), "aliases": []}
                logger.info(f"Matched '{venue_name}' to bygdegardarna city '{result[0]}'")
                save_venue_mapping(venue_name, city_venue.get("qid", ""), city_venue.get("lat"), city_venue.get("lng"), date_str, gmaps_url=gmaps_url, permalink=permalink)
                return result[0], city_venue
    
    return None, None