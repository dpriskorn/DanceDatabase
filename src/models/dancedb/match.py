"""Match venues from various sources to DanceDB."""
import json
import logging
from datetime import date

import config
from src.models.danslogen.fuzzy import fuzzy_match_qid
from src.utils.fuzzy import normalize_for_fuzzy
from src.utils.google_maps import GoogleMaps

logger = logging.getLogger(__name__)


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
