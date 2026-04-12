"""Cogwork operations: scrape and upload events from ALL sources."""
import logging
import sys
from pathlib import Path

import questionary

from src.models.dancedb.status import detect_event_status
from src.models.dancedb_client import DancedbClient

logger = logging.getLogger(__name__)


def get_cogwork_scrapers() -> dict:
    """Discover all cogwork scrapers."""
    scrapers = {}
    scraper_dir = Path(__file__).parent.parent / "cogwork" / "scrapers"

    if not scraper_dir.exists():
        return {}

    for f in scraper_dir.glob("*.py"):
        if f.stem.startswith("_"):
            continue
        module_name = f.stem
        scrapers[module_name] = module_name

    return scrapers


def scrape_cogwork(source: str | None = None) -> None:
    """Scrape cogwork events.

    Args:
        source: Optional specific source, or None for all.
    """
    print("\n=== Scrape cogwork events ===")

    scrapers = get_cogwork_scrapers()
    if not scrapers:
        print("No cogwork scrapers found")
        return

    print(f"Available sources: {', '.join(sorted(scrapers.keys()))}")

    if source and source not in scrapers:
        print(f"Unknown source: {source}")
        return

    sources_to_scrape = [source] if source else list(scrapers.keys())

    print(f"\nScraping {len(sources_to_scrape)} sources...")

    for name in sources_to_scrape:
        print(f"\n{name}: (scraper not fully implemented)")
        print(f"  Note: Run individual scrapers manually")

    print(f"\nTotal: {len(sources_to_scrape)} sources configured")


def upload_cogwork(source: str | None = None, dry_run: bool = False) -> None:
    """Upload cogwork events to DanceDB with confirmation.

    Args:
        source: Optional specific source, or None for all.
        dry_run: If True, preview only.
    """
    print("\n=== Upload cogwork events ===")

    scrapers = get_cogwork_scrapers()
    if not scrapers:
        print("No cogwork scrapers found")
        return

    if dry_run:
        print("DRY RUN - no events will be uploaded")

    print(f"Available sources: {', '.join(sorted(scrapers.keys()))}")

    if source and source not in scrapers:
        print(f"Unknown source: {source}")
        return

    if dry_run:
        print("\nDry run complete. Run without --dry-run to upload.")
        return

    print(f"\nCogwork upload: (not fully implemented)")
    print("Use individual scrapers first, then upload via danslogen if needed")