"""Unified sync commands for all data sources."""

import json
import logging
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

from src.models.dancedb.client import DancedbClient
from src.models.dancedb.ensure_events import EVENTS_DIR, configure_wbi, fetch_events_from_dancedb
from src.models.danslogen.artists.scrape import scrape_artists
from src.models.danslogen.data import DANCEDB_ARTISTS_DIR

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


def get_current_month_year() -> tuple[str, int]:
    """Get current month name and year."""
    today = date.today()
    month_names = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"]
    return month_names[today.month - 1], today.year


@dataclass
class SyncStep:
    name: str
    func: Callable
    input_files: list[Path]
    output_files: list[Path]

    def _has_content(self, f: Path) -> bool:
        """Check if file exists and has content (not empty)."""
        if not f.exists():
            return False
        if f.suffix == ".json":
            try:
                content = f.read_text()
                if content == "[]" or content == "{}" or content.strip() == "":
                    return False
                data = json.loads(content)
                if isinstance(data, (list, dict)) and len(data) == 0:
                    return False
            except json.JSONDecodeError:
                pass
        return True

    def needs_run(self, force: bool = False) -> bool:
        """Check if step needs to run (missing input OR missing output OR empty input)."""
        if force:
            return True
        if not self.input_files:
            return not all(f.exists() for f in self.output_files) if self.output_files else True
        if any(not f.exists() for f in self.input_files):
            return True
        if any(not self._has_content(f) for f in self.input_files):
            return True
        if not self.output_files:
            return True
        return any(not f.exists() for f in self.output_files)

    def run(self, force: bool = False) -> None:
        """Run the step if needed."""
        print(f"\n[RUN] {self.name}")
        self.func()


def get_data_dir() -> Path:
    """Get the data directory path."""
    import config

    return config.data_dir


def run_sync_steps(
    steps: list[SyncStep],
    only_scrape: bool = False,
) -> None:
    """Run a list of sync steps with prerequisite checking."""
    for step in steps:
        step.run()


def scrape_all(month: str, year: int) -> None:
    """Scrape all data sources first."""
    from src.models.cogwork.scrape import scrape as scrape_cogwork
    from src.models.dancedb.venue_ops import scrape_bygdegardarna
    from src.models.danslogen.events.scrape import scrape_danslogen
    from src.models.folketshus.venue import run as scrape_folketshus
    from src.models.onbeat.run import run as scrape_onbeat
    from src.models.wikidata.operations import scrape_wikidata_artists

    date_str = date.today().strftime("%Y-%m-%d")
    get_data_dir()

    print("\n" + "=" * 50)
    print("SCRAPING ALL DATA SOURCES")
    print("=" * 50)

    print("\n[1/6] Scrape Wikidata artists...")
    scrape_wikidata_artists(date_str=date_str)

    print("\n[2/6] Scrape danslogen events...")
    scrape_danslogen(month=month, year=year)

    print("\n[3/6] Scrape bygdegardarna venues...")
    scrape_bygdegardarna(date_str=date_str)

    print("\n[4/6] Scrape onbeat events...")
    scrape_onbeat()

    print("\n[5/6] Scrape cogwork events...")
    scrape_cogwork(source=None)

    print("\n[6/6] Scrape folketshus venues...")
    scrape_folketshus(date_str=date_str, match=False)

    print("\n" + "=" * 50)
    print("SCRAPING COMPLETE")
    print("=" * 50)


def sync_danslogen(
    month: str | None = None,
    year: int | None = None,
    limit: int | None = None,
    only_scrape: bool = False,
) -> bool:
    """Sync danslogen events with prerequisite checking."""
    from src.models.dancedb.venue_ops import ensure_artists, ensure_venues, match_venues, scrape_bygdegardarna, scrape_dancedb_venues
    from src.models.danslogen.events.scrape import scrape_danslogen, upload_events
    from src.models.folketshus.venue import run as scrape_folketshus
    from src.models.wikidata.operations import scrape_wikidata_artists, sync_wikidata_artists

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

    steps = [
        SyncStep(
            "0. Fetch DanceDB artists",
            lambda: fetch_dancedb_artists(date_str=date_str),
            input_files=[],
            output_files=[dancedb_artists_file],
        ),
        SyncStep(
            "1. Scrape danslogen artists",
            lambda: scrape_artists(date_str=date_str),
            input_files=[],
            output_files=[],
        ),
        SyncStep(
            "2. Scrape Wikidata artists",
            lambda: scrape_wikidata_artists(date_str=date_str),
            input_files=[],
            output_files=[wikidata_file],
        ),
        SyncStep(
            "3. Sync Wikidata artists",
            lambda: sync_wikidata_artists(date_str=date_str),
            input_files=[dancedb_artists_file, wikidata_file],
            output_files=[],
        ),
        SyncStep(
            "4. Scrape danslogen events",
            lambda: scrape_danslogen(month=month, year=year),
            input_files=[],
            output_files=[danslogen_event_file],
        ),
        SyncStep(
            "5. Scrape bygdegardarna venues",
            lambda: scrape_bygdegardarna(date_str=date_str),
            input_files=[],
            output_files=[bygdegardarna_file],
        ),
        SyncStep(
            "6. Scrape folketshus venues",
            lambda: scrape_folketshus(date_str=date_str, match=True),
            input_files=[],
            output_files=[],
        ),
        SyncStep(
            "7. Fetch DanceDB venues",
            lambda: scrape_dancedb_venues(date_str=date_str),
            input_files=[],
            output_files=[dancedb_venues_file],
        ),
        SyncStep(
            "8. Match venues to DanceDB",
            lambda: match_venues(date_str=date_str, skip_prompts=True),
            input_files=[bygdegardarna_file, dancedb_venues_file],
            output_files=[enriched_file],
        ),
        SyncStep(
            "9. Ensure venues exist",
            lambda: ensure_venues(date_str=date_str),
            input_files=[danslogen_event_file],
            output_files=[venues_file],
        ),
        SyncStep(
            "10. Ensure artists exist",
            lambda: ensure_artists(date_str=date_str),
            input_files=[danslogen_event_file],
            output_files=[],
        ),
        SyncStep(
            "11. Fetch DanceDB events",
            lambda: fetch_dancedb_events(date_str=date_str),
            input_files=[],
            output_files=[dancedb_events_file],
        ),
        SyncStep(
            "12. Upload events",
            lambda: upload_events(
                input_file=str(danslogen_event_file),
                date_str=date_str,
                month=month,
                limit=limit,
            ),
            input_files=[danslogen_event_file, dancedb_events_file],
            output_files=[],
        ),
    ]

    run_sync_steps(steps, only_scrape=only_scrape)

    print("\n" + "=" * 50)
    print("DANSLOGEN SYNC COMPLETE")
    print("=" * 50)
    return True


def sync_bygdegardarna(
    only_scrape: bool = False,
) -> bool:
    """Sync bygdegardarna venues with prerequisite checking."""
    from src.models.dancedb.venue_ops import match_venues, scrape_bygdegardarna, scrape_dancedb_venues

    date_str = date.today().strftime("%Y-%m-%d")
    data_dir = get_data_dir()

    bygdegardarna_file = data_dir / "bygdegardarna" / f"{date_str}.json"
    dancedb_venues_file = data_dir / "dancedb" / "venues" / f"{date_str}.json"
    enriched_file = data_dir / "bygdegardarna" / "enriched" / f"{date_str}.json"

    print("\n" + "=" * 50)
    print("SYNC BYGDEGARDARNA")
    print("=" * 50)

    steps = [
        SyncStep(
            "1. Scrape bygdegardarna venues",
            lambda: scrape_bygdegardarna(date_str=date_str),
            input_files=[],
            output_files=[bygdegardarna_file],
        ),
        SyncStep(
            "2. Fetch existing DanceDB venues",
            lambda: scrape_dancedb_venues(date_str=date_str),
            input_files=[],
            output_files=[dancedb_venues_file],
        ),
        SyncStep(
            "3. Match venues to DanceDB",
            lambda: match_venues(date_str=date_str, skip_prompts=True),
            input_files=[bygdegardarna_file, dancedb_venues_file],
            output_files=[enriched_file],
        ),
    ]

    run_sync_steps(steps, only_scrape=only_scrape)

    print("\n" + "=" * 50)
    print("BYGDEGARDARNA SYNC COMPLETE")
    print("=" * 50)
    return True


def sync_onbeat() -> bool:
    """Sync onbeat events: scrape + upload."""
    from src.models.onbeat.run import run as scrape_onbeat

    print("\n" + "=" * 50)
    print("SYNC ONBEAT")
    print("=" * 50)

    scrape_onbeat()

    print("\n" + "=" * 50)
    print("ONBEAT SYNC COMPLETE")
    print("=" * 50)
    return True


def sync_cogwork() -> bool:
    """Sync cogwork events: scrape + upload."""
    from src.models.cogwork.scrape import scrape as scrape_cogwork
    from src.models.cogwork.upload import upload as upload_cogwork

    print("\n" + "=" * 50)
    print("SYNC COGWORK")
    print("=" * 50)

    scrape_cogwork(source=None)

    print("\n[2/2] Upload events...")
    upload_cogwork(source=None)

    print("\n" + "=" * 50)
    print("COGWORK SYNC COMPLETE")
    print("=" * 50)
    return True


def sync_folketshus() -> bool:
    """Sync folketshus venues: scrape + match."""
    from src.models.folketshus.venue import run as scrape_folketshus

    print("\n" + "=" * 50)
    print("SYNC FOLKETSHUS")
    print("=" * 50)

    scrape_folketshus(date_str=None, match=True)

    print("\n" + "=" * 50)
    print("FOLKETSHUS SYNC COMPLETE")
    print("=" * 50)
    return True


def sync_all(
    month: str | None = None,
    year: int | None = None,
    limit: int | None = None,
    only_scrape: bool = False,
) -> bool:
    """Sync all sources with prerequisite checking."""
    if month is None or year is None:
        month, year = get_current_month_year()

    print("\n" + "=" * 60)
    print(f"SYNC ALL SOURCES: {month} {year}")
    print("=" * 60)

    print("\n[0/6] Scraping all data sources...")
    scrape_all(month=month, year=year)

    sources = [
        ("DANSLOGEN", lambda: sync_danslogen(month=month, year=year, limit=limit, only_scrape=only_scrape)),
        ("BYGDEGARDARNA", lambda: sync_bygdegardarna(only_scrape=only_scrape)),
        ("ONBEAT", lambda: sync_onbeat()),
        ("COGWORK", lambda: sync_cogwork()),
        ("FOLKETSHUS", lambda: sync_folketshus()),
    ]

    for i, (name, func) in enumerate(sources, 1):
        print(f"\n{'=' * 60}")
        print(f"SYNCING [{i}/{len(sources)}]: {name}")
        print("=" * 60)
        try:
            func()
        except Exception as e:
            logger.error(f"Failed to sync {name}: %s", e)
            print(f"\nERROR: {name} sync failed: {e}")
            print("\nAborting sync-all. Fix the error and try again.")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("ALL SOURCES SYNC COMPLETE")
    print("=" * 60)
    return True
