from rapidfuzz import fuzz, process
from typing import Optional


def fuzzy_match_qid(venue_name: str, qid_map: dict[str, str], threshold: int = 85) -> Optional[tuple[str, str, int]]:
    """Find best matching QID using token_set_ratio. Handles subset matches well.
    Returns (matched_key, qid, score) or None."""
    if not venue_name:
        return None
    result = process.extractOne(
        venue_name,
        qid_map.keys(),
        scorer=fuzz.token_set_ratio
    )
    if result and result[1] >= threshold:
        return (result[0], qid_map[result[0]], result[1])
    return None
