from typing import Optional

from src.models.dancedb.client import DancedbClient
from src.models.danslogen.data import load_band_map
from src.models.danslogen.fuzzy import fuzzy_match_qid


class BandMapper:
    """Resolves band names to QIDs from DanceDB artists data."""

    def __init__(self, client: Optional[DancedbClient] = None):
        self.client = client
        self._band_map: Optional[dict[str, str]] = None

    def _get_band_map(self) -> dict[str, str]:
        """Get band map, loading from JSON if not cached."""
        if self._band_map is None:
            self._band_map = load_band_map()
        return self._band_map

    def resolve(self, band_name: str) -> Optional[str]:
        """Resolve band name to QID.

        1. Exact match (case-insensitive) against DanceDB artists
        2. Fuzzy match against DanceDB artists
        3. Search in DanceDB (if client provided)
        4. Create new band in DanceDB (if client provided)

        Returns QID or None if not found.
        """
        if not band_name:
            return None

        band_map = self._get_band_map()

        exact = next(
            (qid for key, qid in band_map.items()
             if key.lower() == band_name.lower()),
            None
        )
        if exact:
            return exact

        fuzzy = fuzzy_match_qid(band_name, band_map)
        if fuzzy:
            matched_key, qid, score = fuzzy
            self._band_map[matched_key.lower()] = qid
            return qid

        if self.client is None:
            return None

        try:
            qid = self.client.get_or_create_band(band_name)
            if qid:
                self._band_map[band_name.lower()] = qid
            return qid
        except Exception:
            return None
