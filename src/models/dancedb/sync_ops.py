"""Sync operations for all data sources."""
from datetime import date

from src.models.pipeline import Pipeline


def get_current_month_year() -> tuple[str, int]:
    """Get current month name and year."""
    today = date.today()
    month_names = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"]
    return month_names[today.month - 1], today.year


def get_data_dir() -> Path:
    """Get the data directory path."""
    import config

    return config.data_dir


from pathlib import Path
import logging

from src.models.dancedb.client import DancedbClient
from src.models.dancedb.ensure_events import EVENTS_DIR, configure_wbi, fetch_events_from_dancedb
from src.models.danslogen.artists.scrape import scrape_artists
from src.models.danslogen.data import DANCEDB_ARTISTS_DIR
from src.models.pipeline import Pipeline
from src.models.dancedb.venue_ops import (
    ensure_artists,
    ensure_venues,
    match_venues,
    scrape_bygdegardarna,
    scrape_dancedb_venues,
)
from src.models.danslogen.events.scrape import scrape_danslogen, upload_events
from src.models.folketshus.venue import run as scrape_folketshus
from src.models.wikidata.operations import scrape_wikidata_artists, sync_wikidata_artists

logger = logging.getLogger(__name__)


def fetch_dancedb_artists(date_str: str) -> None:
    """Fetch artists from DanceDB with QIDs."""
    import json

    client = DancedbClient()
    artists = client.fetch_artists_from_dancedb()
    output_file = DANCEDB_ARTISTS_DIR / f"{date_str}.json"
    DANCEDB_ARTISTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(artists, f, ensure_ascii=False, indent=2)
    print(f"Fetched {len(artists)} artists from DanceDB")
    print(f"Saved to {output_file}")


def fetch_dancedb_events(date_str: str) -> None:
    """Fetch existing events from DanceDB for deduplication."""
    import json

    configure_wbi()
    events = fetch_events_from_dancedb()
    output_file = EVENTS_DIR / f"{date_str}.json"
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    print(f"Fetched {len(events)} events from DanceDB")
    print(f"Saved to {output_file}")
