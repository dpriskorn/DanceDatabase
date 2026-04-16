from typing import Optional

from rapidfuzz import fuzz, process

from src.utils.fuzzy import normalize_for_fuzzy


def fuzzy_match_qid(venue_name: str, qid_map: dict[str, str], threshold: int | None = None, remove_terms: list[str] | None = None) -> Optional[tuple[str, str, int, str]]:
    if threshold is None:
        from config import FUZZY_THRESHOLD_VENUE_DANSLOGEN

        threshold = FUZZY_THRESHOLD_VENUE_DANSLOGEN
    """Find best matching QID using token_set_ratio. Handles subset matches well.
    Returns (matched_key, qid, score, cleaned_input) or None."""
    if not venue_name:
        return None
    
    normalized_input = normalize_for_fuzzy(venue_name, remove_terms)
    
    normalized_map = {normalize_for_fuzzy(k, remove_terms): (k, qid) for k, qid in qid_map.items()}
    
    result = process.extractOne(normalized_input, normalized_map.keys(), scorer=fuzz.token_set_ratio)
    if result and result[1] >= threshold:
        original_key = normalized_map[result[0]][0]
        return (original_key, qid_map[original_key], result[1], normalized_input)
    return None
