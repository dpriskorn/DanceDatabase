import logging
from typing import Optional

from src.models.dancedb.client import DancedbClient
from src.models.danslogen.data import load_venue_map
from src.models.danslogen.fuzzy import fuzzy_match_qid

logger = logging.getLogger(__name__)


class VenueMapper:
    """Resolves venue names to QIDs from DanceDB venues data."""

    def __init__(self, client: Optional[DancedbClient] = None):
        self.client = client
        self._venue_map: Optional[dict[str, str]] = None

    def _get_venue_map(self) -> dict[str, str]:
        """Get venue map, loading from JSON if not cached."""
        if self._venue_map is None:
            try:
                self._venue_map = load_venue_map()
            except Exception as e:
                logger.warning("Could not load venue map from JSON: %s", e)
                self._venue_map = {}
        return self._venue_map

    def resolve(self, venue_name: str) -> Optional[str]:
        """Resolve venue name to QID.

        1. Exact match (case-insensitive) against DanceDB venues
        2. Fuzzy match against DanceDB venues

        Returns QID or None if not found.
        """
        if not venue_name:
            return None

        venue_map = self._get_venue_map()

        exact = next((qid for key, qid in venue_map.items() if key.lower() in venue_name.lower() or venue_name.lower() in key.lower()), None)
        if exact:
            logger.debug("Venue exact match: '%s' -> %s", venue_name, exact)
            return exact

        logger.debug("Venue no exact match, trying fuzzy: '%s'", venue_name)
        fuzzy = fuzzy_match_qid(venue_name, venue_map)
        if fuzzy:
            matched_key, qid, score = fuzzy
            logger.debug("Venue fuzzy match: '%s' -> '%s' (%s%%)", venue_name, matched_key, score)
            self._venue_map[matched_key.lower()] = qid
            return qid

        logger.debug("Venue not found: '%s' (tried %d venues)", venue_name, len(venue_map))
        return None
