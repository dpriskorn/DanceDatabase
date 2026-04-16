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


def is_false_fuzzy_match(cleaned_input: str, cleaned_match: str) -> bool:
    """Check if cleaned terms are known false friends."""
    false_friends = getattr(config, "FUZZY_FALSE_FRIENDS", {})
    return cleaned_match in false_friends.get(cleaned_input, [])