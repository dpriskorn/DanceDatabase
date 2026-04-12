"""Orchestrator for full DanceDB workflow."""
import logging
from datetime import date

from src.models.commands.venue_ops import (
    scrape_bygdegardarna,
    scrape_dancedb_venues,
    match_venues,
)
from src.models.danslogen.event_ops import (
    upload_events,
)

logger = logging.getLogger(__name__)


def run_all(
    month: str = "april",
    year: int = 2026,
    dry_run: bool = False,
    limit: int | None = None,
) -> None:
    """Run full workflow: scrape → match → upload.

    Step 1: Scrape bygdegardarna venues (with coords)
    Step 2: Scrape DanceDB venues
    Step 3: Match venues
    Step 4: Scrape danslogen events (if needed)
    Step 5: Ensure venues exist
    Step 6: Upload events
    """
    date_str = date.today().strftime("%Y-%m-%d")

    print("=" * 50)
    print("DANCEDB FULL WORKFLOW")
    print("=" * 50)

    if dry_run:
        print("\n*** DRY RUN - NO CHANGES WILL BE MADE ***\n")

    print("\n[1/4] Scraping bygdegardarna venues...")
    scrape_bygdegardarna(date_str)

    print("\n[2/4] Scraping DanceDB venues...")
    scrape_dancedb_venues(date_str)

    print("\n[3/4] Matching venues to DanceDB...")
    match_venues(date_str, skip_prompts=True)

    print("\n[4/4] Uploading events to DanceDB...")
    input_file = f"data/danslogen/{month.lower()}.json"
    upload_events(
        input_file=input_file,
        date_str=date_str,
        month=month,
        dry_run=dry_run,
        limit=limit,
    )

    print("\n" + "=" * 50)
    print("WORKFLOW COMPLETE")
    print("=" * 50)