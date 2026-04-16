import json
import logging
from datetime import date
from pathlib import Path
from typing import Optional

import config

logger = logging.getLogger(__name__)


class DataNotFoundError(Exception):
    """Raised when required JSON data file is not found."""

    pass


class DanslogenData:
    """Loads data from JSON files for danslogen processing."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self._band_map: Optional[dict[str, str]] = None
        self._venue_map: Optional[dict[str, str]] = None

    @staticmethod
    def get_today_str() -> str:
        return date.today().strftime("%Y-%m-%d")

    def load_band_map(self) -> dict[str, str]:
        """Load band QID map from DanceDB artists JSON file for today.

        Returns dict mapping band name (label) to QID.
        Raises DataNotFoundError if today's data file is not found.
        """
        if self._band_map is not None:
            return self._band_map

        today = self.get_today_str()
        artists_file = config.dancedb_artists_dir / f"{today}.json"
        if not config.dancedb_artists_dir.exists():
            raise DataNotFoundError(f"DanceDB artists directory not found: {config.dancedb_artists_dir}")
        if not artists_file.exists():
            raise DataNotFoundError(f"Artists data file not found for today: {artists_file}")

        try:
            artists = json.loads(artists_file.read_text())
            band_map = {}
            for artist in artists:
                qid = artist.get("qid", "")
                label = artist.get("label", "")
                if qid and label:
                    band_map[label.lower()] = qid
                for alias in artist.get("aliases", []):
                    if alias and qid:
                        band_map[alias.lower()] = qid
            logger.info(f"Loaded {len(band_map)} band mappings from {artists_file.name}")
            self._band_map = band_map
            return band_map
        except Exception as e:
            raise DataNotFoundError(f"Failed to load artists from {artists_file}: {e}")

    def load_venue_map(self) -> dict[str, str]:
        """Load venue QID map from DanceDB venues JSON file for today.

        Returns dict mapping venue name (label) to QID.
        Raises DataNotFoundError if today's data file is not found.
        """
        if self._venue_map is not None:
            return self._venue_map

        today = self.get_today_str()
        venues_file = config.dancedb_venues_dir / f"{today}.json"
        if not config.dancedb_venues_dir.exists():
            raise DataNotFoundError(f"DanceDB venues directory not found: {config.dancedb_venues_dir}")
        if not venues_file.exists():
            raise DataNotFoundError(f"Venues data file not found for today: {venues_file}")

        try:
            venues = json.loads(venues_file.read_text())
            venue_map = {}
            for qid, venue_data in venues.items():
                label = venue_data.get("label", "")
                if label:
                    venue_map[label.lower()] = qid
                for alias in venue_data.get("aliases", []):
                    if alias:
                        venue_map[alias.lower()] = qid
            logger.info(f"Loaded {len(venue_map)} venue mappings from {venues_file.name}")
            self._venue_map = venue_map
            return venue_map
        except Exception as e:
            raise DataNotFoundError(f"Failed to load venues from {venues_file}: {e}")

    def load_bygdegardarna_venues(self, date_str: str) -> dict[str, dict]:
        """Load venues from bygdegardarna scrape (has coordinates).

        Returns: dict[title_lower -> venue_dict]
        """
        path = config.bygdegardarna_dir / f"{date_str}.json"
        if not path.exists():
            logger.warning(f"Bygdegardarna venues not found: {path}")
            return {}
        venues = json.loads(path.read_text())
        return {v.get("title", "").lower(): v for v in venues if v.get("title")}

    def load_matched_venues(self, date_str: str) -> dict[str, dict]:
        """Load matched venues from bygdegardarna enrichment (has QIDs).

        Returns: dict[title -> venue_dict]
        """
        path = config.bygdegardarna_enriched_dir / f"{date_str}.json"
        if not path.exists():
            logger.warning(f"Matched venues not found: {path}")
            return {}
        venues = json.loads(path.read_text())
        return {v.get("title", ""): v for v in venues if v.get("title") and v.get("qid")}

    def load_folketshus_venues(self, date_str: str) -> dict[str, dict]:
        """Load venues from folketshus enriched data (has coordinates + QIDs).

        Returns: dict[name_lower -> venue_dict]
        """
        available_files = sorted(config.folketshus_enriched_dir.glob("*.json"), reverse=True)
        
        path = None
        for check_path in available_files:
            if check_path.exists():
                venues = json.loads(check_path.read_text())
                if len(venues) >= 100:
                    path = check_path
                    break
                path = check_path
        
        if not path or not path.exists():
            logger.warning("Folketshus venues not found")
            return {}
        venues = json.loads(path.read_text())
        logger.info(f"Loaded {len(venues)} folketshus venues from {path.name}")
        return {v.get("name", "").lower(): v for v in venues if v.get("name")}

    def load_dancedb_venues(self, date_str: str) -> dict[str, dict]:
        """Load DanceDB venues from scrape.

        Returns: dict[qid -> venue_dict]
        """
        path = config.dancedb_venues_dir / f"{date_str}.json"
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


_data_instance: Optional[DanslogenData] = None


def _get_data_instance() -> DanslogenData:
    global _data_instance
    if _data_instance is None:
        _data_instance = DanslogenData()
    return _data_instance


def _reset_instance() -> None:
    global _data_instance
    _data_instance = None


def load_band_map() -> dict[str, str]:
    """Load band QID map from DanceDB artists JSON file for today.

    Returns dict mapping band name (label) to QID.
    Raises DataNotFoundError if today's data file is not found.
    """
    return _get_data_instance().load_band_map()


def load_venue_map() -> dict[str, str]:
    """Load venue QID map from DanceDB venues JSON file for today.

    Returns dict mapping venue name (label) to QID.
    Raises DataNotFoundError if today's data file is not found.
    """
    return _get_data_instance().load_venue_map()


def load_danslogen_artists() -> dict[str, dict]:
    """Load danslogen artists with spelplan_id.

    Returns dict mapping band name (lowercase) to {name, spelplan_id}.
    """
    today = get_today_str()
    artists_file = config.danslogen_artists_dir / f"{today}.json"
    if not artists_file.exists():
        logger.warning(f"Danslogen artists file not found: {artists_file}")
        return {}

    artists_data = json.loads(artists_file.read_text())
    artists_map = {}
    for a in artists_data:
        name = a.get("name", "")
        if name:
            artists_map[name.lower()] = {
                "name": name,
                "spelplan_id": a.get("spelplan_id", ""),
            }
    logger.info(f"Loaded {len(artists_map)} danslogen artists")
    return artists_map


def get_today_str() -> str:
    return date.today().strftime("%Y-%m-%d")
