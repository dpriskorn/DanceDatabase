"""Sync for danslogen data source."""
from datetime import date
from pathlib import Path

from src.models.pipeline import Pipeline
from src.models.dancedb.client import DancedbClient
from src.models.dancedb.ensure_events import EVENTS_DIR, configure_wbi, fetch_events_from_dancedb
from src.models.danslogen.artists.scrape import scrape_artists
from src.models.danslogen.data import DANCEDB_ARTISTS_DIR
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


def get_current_month_year() -> tuple[str, int]:
    """Get current month name and year."""
    today = date.today()
    month_names = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"]
    return month_names[today.month - 1], today.year


def get_data_dir() -> Path:
    """Get the data directory path."""
    import config

    return config.data_dir


def sync_danslogen(
    month: str | None = None,
    year: int | None = None,
    limit: int | None = None,
    only_scrape: bool = False,
) -> bool:
    """Sync danslogen events with prerequisite checking."""
    import logging

    if month is None or year is None:
        month, year = get_current_month_year()

    date_str = date.today().strftime("%Y-%m-%d")
    data_dir = get_data_dir()

    dancedb_artists_file = data_dir / "dancedb" / "artists" / f"{date_str}.json"
    wikidata_file = data_dir / "wikidata" / "artists" / f"{date_str}.json"
    danslogen_event_file = data_dir / "danslogen" / "events" / f"{date_str}-{month.lower()}.json"
    venues_file = data_dir / "dancedb" / "venues" / f"{date_str}.json"
    dancedb_events_file = EVENTS_DIR / f"{date_str}.json"

    bygdegardarna_file = data_dir / "bygdegardarna" / f"{date_str}.json"
    dancedb_venues_file = data_dir / "dancedb" / "venues" / f"{date_str}.json"
    enriched_file = data_dir / "bygdegardarna" / "enriched" / f"{date_str}.json"

    print("\n" + "=" * 50)
    print(f"SYNC DANSLOGEN: {month} {year}")
    print("=" * 50)

    pipeline = Pipeline(name="danslogen")
    pipeline.add_step(
        "0. Fetch DanceDB artists",
        lambda: fetch_dancedb_artists(date_str=date_str),
        output_files=[dancedb_artists_file],
    )
    pipeline.add_step(
        "1. Scrape danslogen artists",
        lambda: scrape_artists(date_str=date_str),
    )
    pipeline.add_step(
        "2. Scrape Wikidata artists",
        lambda: scrape_wikidata_artists(date_str=date_str),
        output_files=[wikidata_file],
    )
    pipeline.add_step(
        "3. Sync Wikidata artists",
        lambda: sync_wikidata_artists(date_str=date_str),
        input_files=[dancedb_artists_file, wikidata_file],
    )
    pipeline.add_step(
        "4. Scrape danslogen events",
        lambda: scrape_danslogen(month=month, year=year),
        output_files=[danslogen_event_file],
    )
    pipeline.add_step(
        "5. Scrape bygdegardarna venues",
        lambda: scrape_bygdegardarna(date_str=date_str),
        output_files=[bygdegardarna_file],
    )
    pipeline.add_step(
        "6. Scrape folketshus venues",
        lambda: scrape_folketshus(date_str=date_str),
    )
    pipeline.add_step(
        "7. Fetch DanceDB venues",
        lambda: scrape_dancedb_venues(date_str=date_str),
        output_files=[dancedb_venues_file],
    )
    pipeline.add_step(
        "8. Match venues to DanceDB",
        lambda: match_venues(date_str=date_str, skip_prompts=True),
        input_files=[bygdegardarna_file, dancedb_venues_file],
        output_files=[enriched_file],
    )
    pipeline.add_step(
        "9. Ensure venues exist",
        lambda: ensure_venues(date_str=date_str),
        input_files=[danslogen_event_file],
        output_files=[venues_file],
    )
    pipeline.add_step(
        "10. Ensure artists exist",
        lambda: ensure_artists(date_str=date_str),
        input_files=[danslogen_event_file],
    )
    pipeline.add_step(
        "11. Fetch DanceDB events",
        lambda: fetch_dancedb_events(date_str=date_str),
        output_files=[dancedb_events_file],
    )
    pipeline.add_step(
        "12. Upload events",
        lambda: upload_events(
            input_file=str(danslogen_event_file),
            date_str=date_str,
            month=month,
            limit=limit,
        ),
        input_files=[danslogen_event_file, dancedb_events_file],
    )

    pipeline.run(only_scrape=only_scrape)

    print("\n" + "=" * 50)
    print("DANSLOGEN SYNC COMPLETE")
    print("=" * 50)
    return True
