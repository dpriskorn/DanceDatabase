"""Onbeat scraper commands."""
import logging
import sys

import questionary

from src.models.dancedb.status import detect_event_status
from src.models.dancedb_client import DancedbClient

logger = logging.getLogger(__name__)


def run(dry_run: bool = False) -> None:
    """Fetch onbeat events."""
    print("\n=== Scrape onbeat events ===")

    try:
        from src.models.onbeat.events import OnbeatEvents
    except ImportError:
        print("Error: onbeat module not available")
        return

    page_url = "https://onbeat.dance/"
    try:
        events = OnbeatEvents(page_url=page_url)
        events.fetch_page()
        events.parse_events()
        event_list = events.events
    except Exception as e:
        print(f"Error fetching onbeat events: {e}")
        print("Note: onbeat.dance may have changed their URL structure")
        return

    if not event_list:
        print("No onbeat events found.")
        return

    print(f"Found {len(event_list)} onbeat events")

    if dry_run:
        print("\nDry run complete. Run without --dry-run to upload.")
        return

    client = DancedbClient()
    uploaded = 0
    skipped = 0

    for i, event in enumerate(event_list, start=1):
        label = event.get("label", {}).get("sv", "Untitled")
        venue = event.get("location", "")

        print(f"\n[{i}/{len(event_list)}] {label}")
        print(f"  Location: {venue}")

        confirm = questionary.rawselect(
            "Upload to DanceDB?",
            choices=["Yes (Recommended)", "Skip", "Skip all", "Abort"]
        ).ask()

        if confirm == "Skip":
            skipped += 1
            continue
        elif confirm == "Skip all":
            print(f"Skipping remaining {len(event_list) - i} events...")
            skipped += len(event_list) - i
            break
        elif confirm == "Abort":
            print("Aborting...")
            sys.exit(0)

        print(f"  (Onbeat upload not implemented - skipping)")
        skipped += 1

    print(f"\nDone! Uploaded {uploaded} events, {skipped} skipped.")