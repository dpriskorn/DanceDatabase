from typing import Optional

import config
from src.models.dancedb.client import DancedbClient
from src.models.danslogen.data import load_band_map, load_danslogen_artists
from src.models.danslogen.fuzzy import fuzzy_match_qid


class BandMapper:
    """Resolves band names to QIDs from DanceDB artists data."""

    def __init__(self, client: Optional[DancedbClient] = None):
        self.client = client
        self._band_map: Optional[dict[str, str]] = None
        self._danslogen_artists: Optional[dict[str, dict]] = None

    def _get_band_map(self) -> dict[str, str]:
        """Get band map, loading from JSON if not cached."""
        if self._band_map is None:
            self._band_map = load_band_map()
        return self._band_map

    def _get_danslogen_artists(self) -> dict[str, dict]:
        """Get danslogen artists with spelplan_id."""
        if self._danslogen_artists is None:
            self._danslogen_artists = load_danslogen_artists()
        return self._danslogen_artists

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

        exact = next((qid for key, qid in band_map.items() if key.lower() == band_name.lower()), None)
        if exact:
            return exact

        fuzzy = fuzzy_match_qid(band_name, band_map, threshold=config.FUZZY_THRESHOLD_ARTIST_DANSLOGEN, remove_terms=config.FUZZY_REMOVE_TERMS_ARTIST_DANSLOGEN)
        if fuzzy:
            self._band_map[fuzzy.matched_label.lower()] = fuzzy.qid
            return fuzzy.qid

        if self.client is None:
            return None

        danslogen_artists = self._get_danslogen_artists()
        spelplan_id = danslogen_artists.get(band_name.lower(), {}).get("spelplan_id", "")

        try:
            qid = self.client.get_or_create_band(band_name, spelplan_id=spelplan_id)
            if qid:
                self._band_map[band_name.lower()] = qid
            return qid
        except Exception:
            return None
