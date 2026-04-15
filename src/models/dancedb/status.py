"""Event status detection utility."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

SEARCH_TERMS = ["inställt", "avbokat", "ställt in", "inställda"]

STATUS_PLANNED = "Q566"
STATUS_CANCELLED = "Q567"


def detect_event_status(text: Optional[str]) -> tuple[str, Optional[str]]:
    """Detect event status from text.

    Searches for cancellation terms in text.
    Default to planned if no terms found.

    Args:
        text: Text to search in (e.g., label + description)

    Returns:
        tuple(status_qid, search_term)
        - If term found: (Q567, term)
        - Otherwise: (Q566, None)
    """
    if not text:
        return STATUS_PLANNED, None

    text_lower = text.lower()
    for term in SEARCH_TERMS:
        if term in text_lower:
            logger.info(
                "Event status '%s' detected (term '%s' found in: '%.50s...')",
                STATUS_CANCELLED, term, text
            )
            return STATUS_CANCELLED, term

    return STATUS_PLANNED, None