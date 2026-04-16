import logging
from pathlib import Path
from typing import Optional

from src.utils.venue_resolver import UnifiedVenueResolver, VenueSourceData

logger = logging.getLogger(__name__)


class VenueResolver:
    """Resolves venue names to QIDs using DanceDB, Folketshus, and Bygdegardarna datasets.

    This class is now a compatibility wrapper around UnifiedVenueResolver.
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self._resolver: Optional[UnifiedVenueResolver] = None

    def _get_resolver(self) -> UnifiedVenueResolver:
        if self._resolver is None:
            self._resolver = UnifiedVenueResolver(data_dir=str(self.data_dir))
        return self._resolver

    def lookup(self, venue_name: str) -> tuple[str | None, str | None]:
        """Look up venue QID from local datasets.

        Returns (qid, external_id) or (None, None) if not found.
        """
        if not venue_name:
            return None, None

        resolver = self._get_resolver()
        data = resolver._ensure_data_loaded()

        for qid, v in data.dancedb.items():
            label = v.get("label", "").lower()
            if venue_name.lower() == label:
                return qid, None
            for alias in v.get("aliases", []):
                if venue_name.lower() == alias.lower():
                    return qid, None

        for v in data.folketshus:
            if venue_name.lower() == v.get("name", "").lower():
                return v.get("qid"), v.get("external_id")

        for v in data.bygdegardarna:
            if venue_name.lower() == v.get("title", "").lower():
                external_id = f"bygdegardarna:{v['meta'].get('permalink', '')}"
                return None, external_id

        return None, None

    def resolve(self, venue_name: str) -> tuple[str, str | None]:
        """Get venue QID. Returns (qid, external_id)."""
        qid, external_id = self.lookup(venue_name)
        if qid:
            return qid, external_id
        if not venue_name:
            return "", None
        logger.warning(f"Venue not found in any dataset: '{venue_name}'")
        return "", external_id
