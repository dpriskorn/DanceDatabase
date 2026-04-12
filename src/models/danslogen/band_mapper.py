import logging
from typing import Optional

from src.models.dancedb_client import DancedbClient
from src.models.danslogen.maps import BAND_QID_MAP, fuzzy_match_qid

logger = logging.getLogger(__name__)


class BandMapper:
    """Resolves band names to QIDs from static map + DanceDB."""

    def __init__(self, client: Optional[DancedbClient] = None):
        self.client = client

    def resolve(self, band_name: str) -> Optional[str]:
        """Resolve band name to QID.

        1. Exact match (case-insensitive) against static map
        2. Fuzzy match against static map
        3. Search in DanceDB (if client provided)
        4. Create new band in DanceDB (if client provided)

        Returns QID or None if not found.
        """
        if not band_name:
            return None

        exact = next(
            (qid for key, qid in BAND_QID_MAP.items()
             if key.lower() == band_name.lower()),
            None
        )
        if exact:
            return exact

        fuzzy = fuzzy_match_qid(band_name, BAND_QID_MAP)
        if fuzzy:
            matched_key, qid, score = fuzzy
            logger.info("Fuzzy matched band '%s' to '%s' (score=%d)", band_name, matched_key, score)
            return qid

        if self.client is None:
            return None

        try:
            qid = self.client.get_or_create_band(band_name)
            if qid:
                logger.info("Added band mapping: %s -> %s", band_name, qid)
            return qid
        except Exception as e:
            logger.warning("Could not get/create band '%s': %s", band_name, e)
            return None