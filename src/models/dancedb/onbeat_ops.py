"""Onbeat operations: scrape and upload events."""
import logging
import subprocess
import sys

import questionary

from src.models.dancedb_client import DancedbClient

logger = logging.getLogger(__name__)


def scrape_onbeat() -> None:
    """Fetch onbeat events."""
    print("\n=== Scrape onbeat events ===")

    result = subprocess.run(
        ["python", "-c", 
         "from src.models.onbeat.events import OnbeatEvents; "
         "e = OnbeatEvents(page_url='https://onbeat.dance/kurser/'); "
         "e.fetch(); e.parse(); print(e.events)"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError("onbeat scrape failed")
    print(result.stdout)
    print("Onbeat events scraped")


def upload_onbeat(dry_run: bool = False) -> None:
    """Upload onbeat events to DanceDB with confirmation."""
    print("\n=== Upload onbeat events ===")

    try:
        from src.models.onbeat.events import OnbeatEvents
    except ImportError:
        print("Error: onbeat module not available")
        return

    if dry_run:
        print("DRY RUN - no events will be uploaded")

    try:
        events = OnbeatEvents(page_url="https://onbeat.dance/kurser/")
        events.fetch()
        events.parse()
        event_list = events.events
    except Exception as e:
        print(f"Error fetching onbeat events: {e}")
        return

    if not event_list:
        print("No onbeat events to upload.")
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