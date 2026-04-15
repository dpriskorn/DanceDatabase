"""Unified sync commands for all data sources."""
import logging
import sys
from datetime import date
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


def get_current_month_year() -> tuple[str, int]:
    """Get current month name and year."""
    today = date.today()
    month_names = ["januari", "februari", "mars", "april", "maj", "juni",
                   "juli", "augusti", "september", "oktober", "november", "december"]
    return month_names[today.month - 1], today.year


@dataclass
class SyncStep:
    name: str
    func: Callable
    input_files: list[Path]
    output_files: list[Path]

    def needs_run(self, force: bool = False) -> bool:
        """Check if any input file is missing."""
        if force:
            return True
        if not self.input_files:
            return True
        return any(not f.exists() for f in self.input_files)

    def run(self, force: bool = False, dry_run: bool = False) -> None:
        """Run the step if needed."""
        if self.needs_run(force):
            print(f"\n[RUN] {self.name}")
            if dry_run:
                print(f"  [DRY RUN] Would execute: {self.func.__name__}")
            else:
                self.func()
        else:
            print(f"\n[SKIP] {self.name} - prerequisites met")


def get_data_dir() -> Path:
    """Get the data directory path."""
    import config
    return config.data_dir


def run_sync_steps(
    steps: list[SyncStep],
    force: bool = False,
    dry_run: bool = False,
    only_scrape: bool = False,
) -> None:
    """Run a list of sync steps with prerequisite checking."""
    for step in steps:
        if only_scrape and step.output_files:
            if all(f.exists() for f in step.output_files):
                print(f"\n[SKIP] {step.name} - output already exists")
                continue
        step.run(force=force, dry_run=dry_run)


def scrape_all(month: str, year: int) -> None:
    """Scrape all data sources first."""
    from src.models.danslogen.event_ops import scrape_danslogen
    from src.models.dancedb.venue_ops import scrape_bygdegardarna
    from src.models.onbeat.run import run as scrape_onbeat
    from src.models.cogwork.scrape import scrape as scrape_cogwork
    from src.models.folketshus.venue import run as scrape_folketshus
    from src.models.wikidata.operations import scrape_wikidata_artists

    date_str = date.today().strftime("%Y-%m-%d")
    data_dir = get_data_dir()

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
    scrape_onbeat(dry_run=False)

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
    dry_run: bool = False,
    limit: int | None = None,
    force: bool = False,
    only_scrape: bool = False,
) -> bool:
    """Sync danslogen events with prerequisite checking."""
    from src.models.danslogen.event_ops import scrape_danslogen, upload_events
    from src.models.dancedb.venue_ops import ensure_venues
    from src.models.wikidata.operations import sync_wikidata_artists

    if month is None or year is None:
        month, year = get_current_month_year()

    date_str = date.today().strftime("%Y-%m-%d")
    data_dir = get_data_dir()

    wikidata_file = data_dir / "wikidata" / "artists" / f"{date_str}.json"
    danslogen_file = data_dir / "danslogen" / f"{month.lower()}.json"
    venues_file = data_dir / "dancedb" / "venues" / f"{date_str}.json"

    print("\n" + "=" * 50)
    print(f"SYNC DANSLOGEN: {month} {year}")
    print("=" * 50)

    if dry_run:
        print("\n*** DRY RUN ***\n")

    steps = [
        SyncStep(
            "1. Sync Wikidata artists",
            lambda: sync_wikidata_artists(date_str=date_str, dry_run=dry_run),
            input_files=[],
            output_files=[wikidata_file],
        ),
        SyncStep(
            "2. Scrape danslogen events",
            lambda: scrape_danslogen(month=month, year=year),
            input_files=[],
            output_files=[danslogen_file],
        ),
        SyncStep(
            "3. Ensure venues exist",
            lambda: ensure_venues(date_str=date_str, dry_run=dry_run),
            input_files=[danslogen_file],
            output_files=[venues_file],
        ),
        SyncStep(
            "4. Upload events",
            lambda: upload_events(
                input_file=str(danslogen_file),
                date_str=date_str,
                month=month,
                dry_run=dry_run,
                limit=limit,
            ),
            input_files=[danslogen_file],
            output_files=[],
        ),
    ]

    run_sync_steps(steps, force=force, dry_run=dry_run, only_scrape=only_scrape)

    print("\n" + "=" * 50)
    print("DANSLOGEN SYNC COMPLETE")
    print("=" * 50)
    return True


def sync_bygdegardarna(
    dry_run: bool = False,
    force: bool = False,
    only_scrape: bool = False,
) -> bool:
    """Sync bygdegardarna venues with prerequisite checking."""
    from src.models.dancedb.venue_ops import (
        scrape_bygdegardarna,
        scrape_dancedb_venues,
        match_venues,
    )

    date_str = date.today().strftime("%Y-%m-%d")
    data_dir = get_data_dir()

    bygdegardarna_file = data_dir / "bygdegardarna" / f"{date_str}.json"
    dancedb_venues_file = data_dir / "dancedb" / "venues" / f"{date_str}.json"

    print("\n" + "=" * 50)
    print("SYNC BYGDEGARDARNA")
    print("=" * 50)

    if dry_run:
        print("\n*** DRY RUN ***\n")

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
            output_files=[],
        ),
    ]

    run_sync_steps(steps, force=force, dry_run=dry_run, only_scrape=only_scrape)

    print("\n" + "=" * 50)
    print("BYGDEGARDARNA SYNC COMPLETE")
    print("=" * 50)
    return True


def sync_onbeat(dry_run: bool = False) -> bool:
    """Sync onbeat events: scrape + upload."""
    from src.models.onbeat.run import run as scrape_onbeat

    print("\n" + "=" * 50)
    print("SYNC ONBEAT")
    print("=" * 50)

    if dry_run:
        print("\n*** DRY RUN ***\n")

    scrape_onbeat(dry_run=dry_run)

    print("\n" + "=" * 50)
    print("ONBEAT SYNC COMPLETE")
    print("=" * 50)
    return True


def sync_cogwork(dry_run: bool = False) -> bool:
    """Sync cogwork events: scrape + upload."""
    from src.models.cogwork.scrape import scrape as scrape_cogwork
    from src.models.cogwork.upload import upload as upload_cogwork

    print("\n" + "=" * 50)
    print("SYNC COGWORK")
    print("=" * 50)

    if dry_run:
        print("\n*** DRY RUN ***\n")

    scrape_cogwork(source=None)

    print("\n[2/2] Upload events...")
    upload_cogwork(source=None, dry_run=dry_run)

    print("\n" + "=" * 50)
    print("COGWORK SYNC COMPLETE")
    print("=" * 50)
    return True


def sync_folketshus(dry_run: bool = False) -> bool:
    """Sync folketshus venues: scrape + match."""
    from src.models.folketshus.venue import run as scrape_folketshus

    print("\n" + "=" * 50)
    print("SYNC FOLKETSHUS")
    print("=" * 50)

    if dry_run:
        print("\n*** DRY RUN ***\n")

    scrape_folketshus(date_str=None, match=True)

    print("\n" + "=" * 50)
    print("FOLKETSHUS SYNC COMPLETE")
    print("=" * 50)
    return True


def sync_all(
    month: str | None = None,
    year: int | None = None,
    dry_run: bool = False,
    limit: int | None = None,
    force: bool = False,
    only_scrape: bool = False,
) -> bool:
    """Sync all sources with prerequisite checking."""
    if month is None or year is None:
        month, year = get_current_month_year()

    print("\n" + "=" * 60)
    print(f"SYNC ALL SOURCES: {month} {year}")
    print("=" * 60)

    if dry_run:
        print("\n*** DRY RUN - NO CHANGES WILL BE MADE ***\n")

    print("\n[0/6] Scraping all data sources...")
    scrape_all(month=month, year=year)

    sources = [
        ("DANSLOGEN", lambda: sync_danslogen(month=month, year=year, dry_run=dry_run, limit=limit, force=force, only_scrape=only_scrape)),
        ("BYGDEGARDARNA", lambda: sync_bygdegardarna(dry_run=dry_run, force=force, only_scrape=only_scrape)),
        ("ONBEAT", lambda: sync_onbeat(dry_run=dry_run)),
        ("COGWORK", lambda: sync_cogwork(dry_run=dry_run)),
        ("FOLKETSHUS", lambda: sync_folketshus(dry_run=dry_run)),
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
