import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class VenueResolver:
    """Resolves venue names to QIDs using DanceDB, Folketshus, and Bygdegardarna datasets."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self._dancedb_venues: dict = {}
        self._folketshus_venues: dict = {}
        self._bygdegardarna_venues: list = []

    def _load_dancedb_venues(self) -> dict:
        """Load venues from local DanceDB JSON cache."""
        if self._dancedb_venues:
            return self._dancedb_venues

        venues_file = self.data_dir / "dancedb/venues/2026-04-12.json"
        if venues_file.exists():
            self._dancedb_venues = json.loads(venues_file.read_text())
            logger.info(f"Loaded {len(self._dancedb_venues)} venues from DanceDB cache")
        return self._dancedb_venues

    def _load_folketshus_venues(self) -> dict:
        """Load venues from Folketshus enriched JSON."""
        if self._folketshus_venues:
            return self._folketshus_venues

        folketshus_file = self.data_dir / "folketshus/enriched/2026-04-14.json"
        if folketshus_file.exists():
            data = json.loads(folketshus_file.read_text())
            self._folketshus_venues = {v["name"].lower(): v for v in data if v.get("qid")}
            logger.info(f"Loaded {len(self._folketshus_venues)} venues from Folketshus")
        return self._folketshus_venues

    def _load_bygdegardarna_venues(self) -> list:
        """Load venues from Bygdegardarna JSON."""
        if self._bygdegardarna_venues:
            return self._bygdegardarna_venues

        bygdegard_file = self.data_dir / "bygdegardarna/2026-04-14.json"
        if bygdegard_file.exists():
            self._bygdegardarna_venues = json.loads(bygdegard_file.read_text())
            logger.info(f"Loaded {len(self._bygdegardarna_venues)} venues from Bygdegardarna")
        return self._bygdegardarna_venues

    def lookup(self, venue_name: str) -> tuple[str | None, str | None]:
        """
        Look up venue QID from local datasets.
        Returns (qid, external_id) or (None, None) if not found.
        """
        if not venue_name:
            return None, None

        venue_lower = venue_name.lower()

        dancedb = self._load_dancedb_venues()
        for qid, v in dancedb.items():
            label = v.get("label", "").lower()
            if venue_lower in label or label in venue_lower:
                logger.debug(f"Matched '{venue_name}' to DanceDB venue '{v['label']}' ({qid})")
                return qid, None

            for alias in v.get("aliases", []):
                if venue_lower in alias or alias in venue_lower:
                    logger.debug(f"Matched '{venue_name}' to DanceDB alias '{alias}' ({qid})")
                    return qid, None

        folketshus = self._load_folketshus_venues()
        for name, v in folketshus.items():
            if venue_lower in name or name in venue_lower:
                logger.debug(f"Matched '{venue_name}' to Folketshus '{v['name']}' ({v.get('qid')})")
                return v.get("qid"), v.get("external_id")

        bygdegard = self._load_bygdegardarna_venues()
        for v in bygdegard:
            title = v.get("title", "").lower()
            if venue_lower in title or title in venue_lower:
                logger.debug(f"Matched '{venue_name}' to Bygdegardarna '{v['title']}'")
                return None, f"bygdegardarna:{v['meta'].get('permalink', '')}"

        logger.debug(f"No match found for venue: '{venue_name}'")
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