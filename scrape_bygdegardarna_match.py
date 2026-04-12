import json
import logging
import math
from datetime import date
from pathlib import Path
from typing import Optional

import questionary
from rapidfuzz import fuzz, process

import config

logging.basicConfig(level=config.loglevel)
logger = logging.getLogger(__name__)

DANCEDB_BASE_URL = "https://dance.wikibase.cloud/wiki/Item"
COORD_THRESHOLD_KM = 1.0
FUZZY_THRESHOLD = 85

OUTPUT_DIR = Path("data") / "bygdegardarna" / "enriched"
UNMATCHED_DIR = Path("data") / "bygdegardarna" / "unmatched"


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def load_data(date_str: str) -> tuple[dict[str, dict], list[dict]]:
    byg_path = Path("data") / "bygdegardarna" / f"{date_str}.json"
    db_path = Path("data") / "dancedb" / "venues" / f"{date_str}.json"

    byg_venues = json.loads(byg_path.read_text())
    db_venues = json.loads(db_path.read_text())
    return db_venues, byg_venues


def exact_match(title: str, db_venues: dict[str, dict]) -> Optional[tuple[str, str]]:
    title_lower = title.lower()
    for qid, data in db_venues.items():
        if data.get("label", "").lower() == title_lower:
            return (qid, data["label"])
    return None


def fuzzy_match(title: str, db_venues: dict[str, dict], threshold: int = FUZZY_THRESHOLD):
    labels = {qid: data["label"] for qid, data in db_venues.items()}
    result = process.extractOne(title, labels.keys(), scorer=fuzz.token_set_ratio)
    if result and result[1] >= threshold:
        return (result[0], labels[result[0]], result[1])
    return None


def coordinate_matches(lat: float, lng: float, db_venues: dict[str, dict], threshold_km: float = COORD_THRESHOLD_KM):
    matches = []
    for qid, data in db_venues.items():
        if data.get("lat") and data.get("lng"):
            dist = haversine_distance(lat, lng, data["lat"], data["lng"])
            if dist <= threshold_km:
                matches.append((qid, data["label"], dist))
    return sorted(matches, key=lambda x: x[2])


def prompt_fuzzy_match(title: str, matched_label: str, qid: str, score: int, permalink: str) -> bool:
    print(f"\nPotential fuzzy match:")
    print(f'  Bygdegardarna: "{title}"')
    print(f'  DanceDB:       "{matched_label}" ({qid})')
    print(f"  Score: {score}")
    print(f"  DanceDB: {DANCEDB_BASE_URL}/{qid}")
    print(f"  Bygdegardarna: {permalink}")
    return questionary.confirm("Accept match?").ask()


def prompt_coordinate_matches(
    title: str, permalink: str, options: list[tuple[str, str, float]]
) -> Optional[str]:
    print(f"\nCoordinate matches within {COORD_THRESHOLD_KM}km:")
    print(f'  Bygdegardarna: "{title}"')
    choices = []
    for qid, label, dist in options:
        choices.append(f"{qid} - \"{label}\" ({dist:.0f}m)")
    choices.append("Skip")
    result = questionary.rawselect("Select:", choices=choices).ask()
    if result == "Skip":
        return None
    return result.split(" - ")[0]


def main(skip_prompts: bool = False):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    UNMATCHED_DIR.mkdir(parents=True, exist_ok=True)

    today_str = date.today().strftime("%Y-%m-%d")
    output_file = OUTPUT_DIR / f"{today_str}.json"
    unmatched_file = UNMATCHED_DIR / f"{today_str}.json"

    if output_file.exists():
        if not questionary.confirm(f"[{today_str}] {output_file} already exists. Skip?").ask():
            output_file.unlink()
        else:
            print(f"Skipping - already matched today.")
            return

    print(f"Loading data from {today_str}...")
    db_venues, byg_venues = load_data(today_str)
    print(f"Loaded {len(db_venues)} DanceDB venues, {len(byg_venues)} bygdegardarna venues")

    enriched = []
    unmatched = []

    for i, venue in enumerate(byg_venues):
        title = venue.get("title", "")
        permalink = venue.get("meta", {}).get("permalink", "")
        lat = venue.get("position", {}).get("lat")
        lng = venue.get("position", {}).get("lng")
        result = {
            "position": venue.get("position"),
            "title": title,
            "meta": venue.get("meta"),
            "permalink": permalink
        }

        qid = None
        match_method = None
        match_score = None

        exact = exact_match(title, db_venues)
        if exact:
            qid, matched_label = exact
            match_method = "exact"
        else:
            fuzzy = fuzzy_match(title, db_venues)
            if fuzzy:
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
            coord_matches = coordinate_matches(lat, lng, db_venues)
            if coord_matches:
                if skip_prompts:
                    if len(coord_matches) == 1:
                        qid = coord_matches[0][0]
                        match_method = "coordinate"
                else:
                    selected = prompt_coordinate_matches(title, permalink, coord_matches)
                    if selected:
                        qid = selected
                        match_method = "coordinate"

        if qid:
            result["qid"] = qid
            result["match_method"] = match_method
            result["match_score"] = match_score
            enriched.append(result)
        else:
            unmatched.append(result)

        if (i + 1) % 50 == 0:
            print(f"Processed {i + 1}/{len(byg_venues)} venues...")

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