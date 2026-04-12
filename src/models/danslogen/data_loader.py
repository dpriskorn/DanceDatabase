import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

BYGDEGARDARNA_DIR = Path("data") / "bygdegardarna"
ENRICHED_BYG_DIR = Path("data") / "bygdegardarna" / "enriched"
DANCEDB_VENUES_DIR = Path("data") / "dancedb" / "venues"


class DanslogenDataLoader:
    """Loads data from JSON files for danslogen processing."""

    def load_bygdegardarna_venues(self, date_str: str) -> dict[str, dict]:
        """Load venues from bygdegardarna scrape (has coordinates).

        Returns: dict[title_lower -> venue_dict]
        """
        path = BYGDEGARDARNA_DIR / f"{date_str}.json"
        if not path.exists():
            logger.warning(f"Bygdegardarna venues not found: {path}")
            return {}
        venues = json.loads(path.read_text())
        return {v.get("title", "").lower(): v for v in venues if v.get("title")}

    def load_matched_venues(self, date_str: str) -> dict[str, dict]:
        """Load matched venues from bygdegardarna enrichment (has QIDs).

        Returns: dict[title -> venue_dict]
        """
        path = ENRICHED_BYG_DIR / f"{date_str}.json"
        if not path.exists():
            logger.warning(f"Matched venues not found: {path}")
            return {}
        venues = json.loads(path.read_text())
        return {v.get("title", ""): v for v in venues if v.get("title") and v.get("qid")}

    def load_dancedb_venues(self, date_str: str) -> dict[str, dict]:
        """Load DanceDB venues from scrape.

        Returns: dict[qid -> venue_dict]
        """
        path = DANCEDB_VENUES_DIR / f"{date_str}.json"
        if not path.exists():
            logger.warning(f"DanceDB venues not found: {path}")
            return {}
        return json.loads(path.read_text())

    def load_rows(self, filename: str) -> list[dict]:
        """Load danslogen rows from JSON file.

        Returns: list of row dicts
        """
        path = Path(filename)
        if not path.exists():
            logger.warning(f"Rows file not found: {path}")
            return []
        return json.loads(path.read_text())