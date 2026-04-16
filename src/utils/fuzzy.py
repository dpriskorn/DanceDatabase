import re
from typing import Optional

import config


def remove_terms(text: str, terms: list[str]) -> str:
    """Remove terms from text case-insensitively."""
    if not text or not terms:
        return text
    pattern = "|".join(re.escape(term) for term in terms)
    return re.sub(pattern, "", text, flags=re.IGNORECASE).strip()


def normalize_for_fuzzy(text: str, remove_terms_list: Optional[list[str]] = None) -> str:
    """Normalize text for fuzzy matching: lowercase, strip, remove terms."""
    if not text:
        return ""
    normalized = text.lower().strip()
    if remove_terms_list:
        normalized = remove_terms(normalized, remove_terms_list)
    return normalized


def is_false_fuzzy_match(cleaned_input: str, cleaned_match: str, remove_terms: list[str] = []) -> bool:
    """Check if cleaned terms are known false friends."""
    false_friends = getattr(config, "FUZZY_FALSE_FRIENDS", {})
    norm_input = normalize_for_fuzzy(cleaned_input, remove_terms)
    for key in false_friends:
        norm_key = normalize_for_fuzzy(key, remove_terms)
        if norm_input == norm_key:
            norm_values = [normalize_for_fuzzy(v, remove_terms) for v in false_friends[key]]
            return cleaned_match in norm_values
    return False