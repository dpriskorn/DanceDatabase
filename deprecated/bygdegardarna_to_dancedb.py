"""bygdegardarna_to_dancedb.py - Match bygdegardarna venues to DanceDB QIDs.

This script:
1. Fetches bygdegardarna venues from their website
2. Fetches DanceDB venues via SPARQL
3. Checks for true duplicates (same name within 10km or missing coordinates)
4. Matches venues using exact, fuzzy, or coordinate matching
"""

import json
import logging
import math
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Optional

import questionary
from rapidfuzz import fuzz, process

import config

logging.basicConfig(level=config.loglevel)
logger = logging.getLogger(__name__)

DANCEDB_ITEM_URL = "https://dance.wikibase.cloud/wiki/Item:"
COORD_THRESHOLD_KM = 1.0
FUZZY_THRESHOLD = 85

OUTPUT_DIR = Path("data") / "bygdegardarna" / "enriched"
UNMATCHED_DIR = Path("data") / "bygdegardarna" / "unmatched"


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate the great-circle distance between two points on Earth.

    Args:
        lat1: Latitude of first point in decimal degrees
        lng1: Longitude of first point in decimal degrees
        lat2: Latitude of second point in decimal degrees
        lng2: Longitude of second point in decimal degrees

    Returns:
        Distance in kilometers
    """
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def fetch_bygdegardarna() -> list[dict]:
    """Fetch all venue locations from bygdegardarna.se website.

    Returns:
        List of venue dictionaries with position, title, and meta fields
    """
    from src.models.bygdegardarna import fetch_markerdata

    return fetch_markerdata()


def fetch_dancedb_venues() -> dict[str, dict]:
    """Fetch all venue items from DanceDB wikibase via SPARQL.

    Queries for venues (instance of Q20) with Swedish labels and coordinates.

    Returns:
        Dictionary mapping QID to venue data with label, lat, lng
    """
    sparql = """
    PREFIX dd: <https://dance.wikibase.cloud/entity/>
    PREFIX ddt: <https://dance.wikibase.cloud/prop/direct/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>

    SELECT ?item ?itemLabel ?geo WHERE {
      ?item ddt:P1 dd:Q20 .
      OPTIONAL { ?item rdfs:label ?itemLabel FILTER(LANG(?itemLabel) = "sv") }
      OPTIONAL { ?item ddt:P4 ?geo }
    }
    ORDER BY ?itemLabel
    LIMIT 2000
    """
    from src.models.dancedb_client import execute_sparql_query

    results = execute_sparql_query(query=sparql)
    venues = {}
    for binding in results["results"]["bindings"]:
        qid = binding["item"]["value"].rsplit("/", 1)[-1]
        label = binding.get("itemLabel", {}).get("value", "")
        geo = binding.get("geo", {}).get("value", "")
        lat, lng = None, None
        if geo:
            coords = geo.replace("Point(", "").replace(")", "").split(" ")
            lng, lat = float(coords[0]), float(coords[1])
        venues[qid] = {"label": label, "lat": lat, "lng": lng}
    return venues


def validate_coordinates(db_venues: dict[str, dict], byg_venues: list[dict]) -> None:
    """Validate that all venues have valid coordinates.

    Reports statistics for each dataset showing count and percentage with coordinates.
    Raises exception if any venue is missing coordinates.

    Args:
        db_venues: Dictionary of DanceDB venues (QID -> label, lat, lng)
        byg_venues: List of bygdegardarna venues

    Raises:
        Exception: If any venue in either dataset is missing coordinates
    """
    db_with_coords = sum(1 for v in db_venues.values() if v.get("lat") and v.get("lng"))
    db_total = len(db_venues)
    db_pct = (db_with_coords / db_total * 100) if db_total else 0
    print(f"  DanceDB: {db_with_coords}/{db_total} ({db_pct:.1f}%) with coordinates")

    byg_with_coords = sum(1 for v in byg_venues if v.get("position", {}).get("lat") and v.get("position", {}).get("lng"))
    byg_total = len(byg_venues)
    byg_pct = (byg_with_coords / byg_total * 100) if byg_total else 0
    print(f"  Bygdegardarna: {byg_with_coords}/{byg_total} ({byg_pct:.1f}%) with coordinates")

    if db_with_coords < db_total or byg_with_coords < byg_total:
        raise Exception("Some venues missing coordinates - cannot proceed")


def check_duplicates(db_venues: dict[str, dict], byg_venues: list[dict]) -> None:
    """Check both datasets for true duplicates.

    A true duplicate is either:
    - Same title/label with coordinates within 10km of each other
    - Missing coordinates entirely (cannot verify uniqueness)

    Note: Coordinates should be validated first using validate_coordinates().

    Args:
        db_venues: Dictionary of DanceDB venues (QID -> label, lat, lng)
        byg_venues: List of bygdegardarna venues

    Raises:
        Exception: If any true duplicates found in either dataset
    """
    DUPLICATE_DISTANCE_KM = 10.0

    # Check DanceDB for duplicates
    label_coords = defaultdict(list)
    for qid, data in db_venues.items():
        label = data.get("label", "").lower()
        lat = data.get("lat")
        lng = data.get("lng")
        if label:
            label_coords[label].append((qid, lat, lng))

    db_true_dupes = []
    for label, entries in label_coords.items():
        if len(entries) > 1:
            for i in range(len(entries)):
                for j in range(i + 1, len(entries)):
                    dist = haversine_distance(entries[i][1], entries[i][2], entries[j][1], entries[j][2])
                    if dist <= DUPLICATE_DISTANCE_KM:
                        db_true_dupes.append((label, [e[0] for e in entries]))
                        break
            if any(d[0] == label for d in db_true_dupes):
                break

    if db_true_dupes:
        print(f"ERROR: Found {len(db_true_dupes)} TRUE duplicates in DanceDB (≤{DUPLICATE_DISTANCE_KM}km):")
        for label, qids in db_true_dupes[:5]:
            print(f"  {label}: {qids}")
        raise Exception("True duplicates found in DanceDB - cannot proceed")

    # Check bygdegardarna for duplicates
    title_coords = defaultdict(list)
    for venue in byg_venues:
        title = venue.get("title", "").lower()
        lat = venue.get("position", {}).get("lat")
        lng = venue.get("position", {}).get("lng")
        if title:
            title_coords[title].append((lat, lng))

    byg_true_dupes = []
    for title, entries in title_coords.items():
        if len(entries) > 1:
            for i in range(len(entries)):
                for j in range(i + 1, len(entries)):
                    dist = haversine_distance(entries[i][0], entries[i][1], entries[j][0], entries[j][1])
                    if dist <= DUPLICATE_DISTANCE_KM:
                        byg_true_dupes.append(title)
                        break

    if byg_true_dupes:
        print(f"ERROR: Found {len(byg_true_dupes)} TRUE duplicates in bygdegardarna (≤{DUPLICATE_DISTANCE_KM}km):")
        for title in byg_true_dupes[:5]:
            print(f"  {title}")
        raise Exception("True duplicates found in bygdegardarna - cannot proceed")


def exact_match(title: str, db_venues: dict[str, dict]) -> Optional[tuple[str, str]]:
    """Find exact title match in DanceDB venues (case-insensitive).

    Args:
        title: Venue title from bygdegardarna
        db_venues: Dictionary of DanceDB venues

    Returns:
        Tuple of (QID, matched label) if exact match found, None otherwise
    """
    title_lower = title.lower()
    for qid, data in db_venues.items():
        if data.get("label", "").lower() == title_lower:
            return (qid, data["label"])
    return None


def fuzzy_match(title: str, db_venues: dict[str, dict], threshold: int = FUZZY_THRESHOLD) -> Optional[tuple[str, str, int]]:
    """Find fuzzy match using token_set_ratio scoring.

    Args:
        title: Venue title from bygdegardarna
        db_venues: Dictionary of DanceDB venues
        threshold: Minimum score to return match (default 85)

    Returns:
        Tuple of (QID, matched label, score) if match above threshold, None otherwise
    """
    labels = {qid: data["label"] for qid, data in db_venues.items()}
    result = process.extractOne(title, labels.keys(), scorer=fuzz.token_set_ratio)
    if result and result[1] >= threshold:
        return (result[0], labels[result[0]], result[1])
    return None


def coordinate_matches(lat: float, lng: float, db_venues: dict[str, dict], threshold_km: float = COORD_THRESHOLD_KM) -> list[tuple[str, str, float]]:
    """Find DanceDB venues within specified distance of given coordinates.

    Args:
        lat: Latitude of bygdegardarna venue
        lng: Longitude of bygdegardarna venue
        db_venues: Dictionary of DanceDB venues
        threshold_km: Maximum distance in km to consider (default 1.0)

    Returns:
        List of tuples (QID, label, distance_km) sorted by distance
    """
    matches = []
    for qid, data in db_venues.items():
        if data.get("lat") and data.get("lng"):
            dist = haversine_distance(lat, lng, data["lat"], data["lng"])
            if dist <= threshold_km:
                matches.append((qid, data["label"], dist))
    return sorted(matches, key=lambda x: x[2])


def prompt_fuzzy_match(title: str, matched_label: str, qid: str, score: int, permalink: str) -> bool:
    """Prompt user to confirm or reject a fuzzy match.

    Args:
        title: Original bygdegardarna venue title
        matched_label: Matched DanceDB venue label
        qid: Matched DanceDB QID
        score: Fuzzy match score
        permalink: URL to bygdegardarna venue page

    Returns:
        True if user accepts match, False if rejected
    """
    print("\nPotential fuzzy match:")
    print(f'  Bygdegardarna: "{title}"')
    print(f'  DanceDB:       "{matched_label}" ({qid})')
    print(f"  Score: {score}")
    print(f"  DanceDB: {DANCEDB_ITEM_URL}{qid}")
    print(f"  Bygdegardarna: {permalink}")
    return questionary.confirm("Accept match?").ask()


def prompt_coordinate_matches(title: str, permalink: str, options: list[tuple[str, str, float]]) -> Optional[str]:
    """Prompt user to select from multiple coordinate-based matches.

    Args:
        title: Original bygdegardarna venue title
        permalink: URL to bygdegardarna venue page
        options: List of (QID, label, distance_km) tuples

    Returns:
        Selected QID, or None if user skips
    """
    print(f"\nCoordinate matches within {COORD_THRESHOLD_KM}km:")
    print(f'  Bygdegardarna: "{title}"')
    choices = []
    for qid, label, dist in options:
        choices.append(f'{qid} - "{label}" ({dist:.0f}m)')
    choices.append("Skip")
    result = questionary.rawselect("Select:", choices=choices).ask()
    if result == "Skip":
        return None
    return result.split(" - ")[0]


def save_bygdegardarna(venues: list[dict]) -> None:
    """Save bygdegardarna venues to JSON file.

    Args:
        venues: List of bygdegardarna venue dictionaries

    Side effect:
        Writes to data/bygdegardarna/YYYY-MM-DD.json
    """
    OUTPUT_DIR.parent.mkdir(parents=True, exist_ok=True)
    today_str = date.today().strftime("%Y-%m-%d")
    path = OUTPUT_DIR.parent / f"{today_str}.json"
    path.write_text(json.dumps(venues, indent=2, ensure_ascii=False) + "\n")


def save_dancedb_venues(venues: dict[str, dict]) -> None:
    """Save DanceDB venues to JSON file.

    Args:
        venues: Dictionary of DanceDB venues (QID -> data)

    Side effect:
        Writes to data/dancedb/venues/YYYY-MM-DD.json
    """
    OUTPUT_DIR.parent.parent.parent.mkdir(parents=True, exist_ok=True)
    today_str = date.today().strftime("%Y-%m-%d")
    path = Path("data") / "dancedb" / "venues" / f"{today_str}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(venues, indent=2, ensure_ascii=False) + "\n")


def _print_progress(
    processed: int, total: int, enriched: list[dict], unmatched: list[dict], matched_qids: set[str], db_venues: dict[str, dict], byg_venues: list[dict]
) -> None:
    """Print matching progress with potential matches remaining."""
    total - processed
    matched = len(enriched)
    unmatched_count = len(unmatched)
    available_qids = len(db_venues) - len(matched_qids)

    {v.get("title", "").lower() for v in byg_venues[:processed]}
    matched_byg_titles = {v.get("title", "").lower() for v in enriched}

    fuzzy_candidates = 0
    coord_candidates = 0
    for venue in byg_venues[processed:]:
        title = venue.get("title", "")
        lat = venue.get("position", {}).get("lat")
        lng = venue.get("position", {}).get("lng")

        if title.lower() not in matched_byg_titles:
            fuzzy = fuzzy_match(title, db_venues)
            if fuzzy and fuzzy[0] not in matched_qids:
                fuzzy_candidates += 1

        if lat and lng and title.lower() not in matched_byg_titles:
            coords = [(q, l, d) for q, l, d in coordinate_matches(lat, lng, db_venues) if q not in matched_qids]
            if coords:
                coord_candidates += 1

    exact_candidates = sum(
        1
        for v in byg_venues[processed:]
        if v.get("title", "").lower() not in matched_byg_titles
        and exact_match(v.get("title", ""), db_venues) is not None
        and exact_match(v.get("title", ""), db_venues)[0] not in matched_qids
    )

    print(
        f"  {processed}/{total} | Matched: {matched} | Unmatched: {unmatched_count} | "
        f"Pending: {exact_candidates} exact, {fuzzy_candidates} fuzzy, {coord_candidates} coord | "
        f"QIDs available: {available_qids}"
    )


def main(skip_prompts: bool = False) -> None:
    """Main entry point for the venue matching workflow.

    Args:
        skip_prompts: If True, skip interactive prompts and auto-match
                      exact and high-confidence fuzzy matches

    Side effects:
        - Fetches data from bygdegardarna.se and DanceDB
        - Saves raw data to JSON files
        - Creates enriched and unmatched output files
    """
    print("Step 1: Fetching bygdegardarna venues...")
    byg_venues = fetch_bygdegardarna()
    print(f"Fetched {len(byg_venues)} bygdegardarna venues")
    save_bygdegardarna(byg_venues)

    print("\nStep 2: Fetching DanceDB venues...")
    db_venues = fetch_dancedb_venues()
    print(f"Fetched {len(db_venues)} DanceDB venues")
    save_dancedb_venues(db_venues)

    print("\nStep 3: Validating coordinates...")
    validate_coordinates(db_venues, byg_venues)

    print("\nStep 4: Checking for duplicates...")
    check_duplicates(db_venues, byg_venues)
    print("No duplicates found.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    UNMATCHED_DIR.mkdir(parents=True, exist_ok=True)

    today_str = date.today().strftime("%Y-%m-%d")
    output_file = OUTPUT_DIR / f"{today_str}.json"
    unmatched_file = UNMATCHED_DIR / f"{today_str}.json"

    if output_file.exists():
        if skip_prompts:
            print("Skipping - already matched today.")
            return
        if not questionary.confirm(f"[{today_str}] {output_file} already exists. Skip?").ask():
            output_file.unlink()
        else:
            print("Skipping - already matched today.")
            return

    print(f"\nStep 5: Matching venues from {today_str}...")
    enriched = []
    unmatched = []
    matched_qids: set[str] = set()
    matched_byg_titles: set[str] = set()

    total = len(byg_venues)
    for i, venue in enumerate(byg_venues):
        title = venue.get("title", "")
        permalink = venue.get("meta", {}).get("permalink", "")
        lat = venue.get("position", {}).get("lat")
        lng = venue.get("position", {}).get("lng")
        result = {"position": venue.get("position"), "title": title, "meta": venue.get("meta"), "permalink": permalink}

        if title in matched_byg_titles:
            unmatched.append(result)
            if (i + 1) % 50 == 0:
                _print_progress(i + 1, total, enriched, unmatched, matched_qids, db_venues, byg_venues)
            continue

        qid = None
        match_method = None
        match_score = None

        exact = exact_match(title, db_venues)
        if exact and exact[0] not in matched_qids:
            qid, matched_label = exact
            match_method = "exact"
        else:
            fuzzy = fuzzy_match(title, db_venues)
            if fuzzy and fuzzy[0] not in matched_qids:
                matched_qid, matched_label, score = fuzzy
                if skip_prompts:
                    if score >= FUZZY_THRESHOLD:
                        qid = matched_qid
                        match_method = "fuzzy"
                        match_score = score
                else:
                    accepted = prompt_fuzzy_match(title, matched_label, matched_qid, score, permalink)
                    if accepted:
                        qid = matched_qid
                        match_method = "fuzzy"
                        match_score = score

        if not qid and lat and lng:
            coord_options = [(qid, label, dist) for qid, label, dist in coordinate_matches(lat, lng, db_venues) if qid not in matched_qids]
            if coord_options:
                if skip_prompts:
                    if len(coord_options) == 1:
                        qid = coord_options[0][0]
                        match_method = "coordinate"
                else:
                    selected = prompt_coordinate_matches(title, permalink, coord_options)
                    if selected:
                        qid = selected
                        match_method = "coordinate"

        if qid:
            matched_qids.add(qid)
            matched_byg_titles.add(title)
            result["qid"] = qid
            result["match_method"] = match_method
            result["match_score"] = match_score
            enriched.append(result)
        else:
            unmatched.append(result)

        if (i + 1) % 50 == 0:
            _print_progress(i + 1, total, enriched, unmatched, matched_qids, db_venues, byg_venues)

    output_file.write_text(json.dumps(enriched, indent=2, ensure_ascii=False) + "\n")
    unmatched_file.write_text(json.dumps(unmatched, indent=2, ensure_ascii=False) + "\n")
    print(f"\nMatched: {len(enriched)} venues")
    print(f"Unmatched: {len(unmatched)} venues")
    print(f"Saved to {output_file}")
    print(f"Unmatched saved to {unmatched_file}")


if __name__ == "__main__":
    import sys

    skip_prompts = "--skip-prompts" in sys.argv
    main(skip_prompts=skip_prompts)
