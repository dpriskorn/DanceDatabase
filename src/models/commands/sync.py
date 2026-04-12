"""Unified sync commands for all data sources."""
import logging
import sys
from datetime import date

logger = logging.getLogger(__name__)


def get_current_month_year() -> tuple[str, int]:
    """Get current month name and year."""
    today = date.today()
    month_names = ["januari", "februari", "mars", "april", "maj", "juni",
                   "juli", "augusti", "september", "oktober", "november", "december"]
    return month_names[today.month - 1], today.year


def sync_danslogen(
    month: str | None = None,
    year: int | None = None,
    dry_run: bool = False,
    limit: int | None = None,
) -> bool:
    """Sync danslogen events: scrape → ensure-venues → upload → ensure-events."""
    from src.models.danslogen.event_ops import scrape_danslogen, upload_events
    from src.models.commands.venue_ops import ensure_venues
    from src.models.commands.ensure_events import run as ensure_events

    if month is None or year is None:
        month, year = get_current_month_year()

    date_str = date.today().strftime("%Y-%m-%d")
    input_file = f"data/danslogen_rows_{year}_{month}.json"

    print("\n" + "=" * 50)
    print(f"SYNC DANSLOGEN: {month} {year}")
    print("=" * 50)

    if dry_run:
        print("\n*** DRY RUN ***\n")

    print("\n[1/4] Scrape danslogen events...")
    scrape_danslogen(month=month, year=year)

    print("\n[2/4] Ensure venues exist in DanceDB...")
    ensure_venues(date_str=date_str, dry_run=dry_run)

    print("\n[3/4] Upload events to DanceDB...")
    upload_events(
        input_file=input_file,
        date_str=date_str,
        month=month,
        dry_run=dry_run,
        limit=limit,
    )

    print("\n[4/4] Ensure all events have venues...")
    ensure_events(month=month, year=year, dry_run=dry_run)

    print("\n" + "=" * 50)
    print("DANSLOGEN SYNC COMPLETE")
    print("=" * 50)
    return True


def sync_bygdegardarna(
    dry_run: bool = False,
) -> bool:
    """Sync bygdegardarna venues: scrape → fetch-dancedb → match-venues."""
    from src.models.commands.venue_ops import (
        scrape_bygdegardarna,
        scrape_dancedb_venues,
        match_venues,
    )

    date_str = date.today().strftime("%Y-%m-%d")

    print("\n" + "=" * 50)
    print("SYNC BYGDEGARDARNA")
    print("=" * 50)

    if dry_run:
        print("\n*** DRY RUN ***\n")

    print("\n[1/3] Scrape bygdegardarna venues...")
    scrape_bygdegardarna(date_str=date_str)

    print("\n[2/3] Fetch existing DanceDB venues...")
    scrape_dancedb_venues(date_str=date_str)

    print("\n[3/3] Match venues to DanceDB...")
    match_venues(date_str=date_str, skip_prompts=True)

    print("\n" + "=" * 50)
    print("BYGDEGARDARNA SYNC COMPLETE")
    print("=" * 50)
    return True


def sync_onbeat(dry_run: bool = False) -> bool:
    """Sync onbeat events: scrape + upload."""
    from src.models.commands.onbeat import run as scrape_onbeat

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
    from src.models.commands.cogwork import scrape as scrape_cogwork, upload as upload_cogwork

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
    from src.models.commands.folketshus import run as scrape_folketshus

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
) -> bool:
    """Sync all sources: bygdegardarna → danslogen → onbeat → cogwork → folketshus."""
    if month is None or year is None:
        month, year = get_current_month_year()

    print("\n" + "=" * 60)
    print(f"SYNC ALL SOURCES: {month} {year}")
    print("=" * 60)

    if dry_run:
        print("\n*** DRY RUN - NO CHANGES WILL BE MADE ***\n")

    sources = [
        ("BYGDEGARDARNA", lambda: sync_bygdegardarna(dry_run=dry_run)),
        ("DANSLOGEN", lambda: sync_danslogen(month=month, year=year, dry_run=dry_run, limit=limit)),
        ("ONBEAT", lambda: sync_onbeat(dry_run=dry_run)),
        ("COGWORK", lambda: sync_cogwork(dry_run=dry_run)),
        ("FOLKETSHUS", lambda: sync_folketshus(dry_run=dry_run)),
    ]

    for name, func in sources:
        print(f"\n{'=' * 60}")
        print(f"SYNCING: {name}")
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
