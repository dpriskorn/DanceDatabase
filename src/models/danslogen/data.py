import json
import logging
from datetime import date
from pathlib import Path

from src.models.dancedb.client import DancedbClient
from src.models.danslogen.fuzzy import fuzzy_match_qid

logger = logging.getLogger(__name__)

DANCEDB_ARTISTS_DIR = Path("data") / "dancedb" / "artists"
DANCEDB_VENUES_DIR = Path("data") / "dancedb" / "venues"


class DataNotFoundError(Exception):
    """Raised when required JSON data file is not found."""
    pass


def get_today_str() -> str:
    return date.today().strftime("%Y-%m-%d")


def load_band_map() -> dict[str, str]:
    """Load band QID map from DanceDB artists JSON file for today.
    
    Returns dict mapping band name (label) to QID.
    Raises DataNotFoundError if today's data file is not found.
    """
    today = get_today_str()
    if not DANCEDB_ARTISTS_DIR.exists():
        raise DataNotFoundError(f"DanceDB artists directory not found: {DANCEDB_ARTISTS_DIR}")
    
    artists_file = DANCEDB_ARTISTS_DIR / f"{today}.json"
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
        return band_map
    except Exception as e:
        raise DataNotFoundError(f"Failed to load artists from {artists_file}: {e}")


def load_venue_map() -> dict[str, str]:
    """Load venue QID map from DanceDB venues JSON file for today.
    
    Returns dict mapping venue name (label) to QID.
    Raises DataNotFoundError if today's data file is not found.
    """
    today = get_today_str()
    if not DANCEDB_VENUES_DIR.exists():
        raise DataNotFoundError(f"DanceDB venues directory not found: {DANCEDB_VENUES_DIR}")
    
    venues_file = DANCEDB_VENUES_DIR / f"{today}.json"
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
        return venue_map
    except Exception as e:
        raise DataNotFoundError(f"Failed to load venues from {venues_file}: {e}")
