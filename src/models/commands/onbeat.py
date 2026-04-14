"""Onbeat scraper commands."""
import json
import logging
import sys
from datetime import date
from pathlib import Path

import questionary

from src.models.dancedb.status import detect_event_status
from src.models.dancedb_client import DancedbClient

logger = logging.getLogger(__name__)

ONBEAT_DATA_DIR = Path("data/onbeat")


def run(dry_run: bool = False) -> None:
    """Fetch onbeat events."""
    print("\n=== Scrape onbeat events ===")

    try:
        from src.models.onbeat.events import OnbeatEvents
    except ImportError:
        print("Error: onbeat module not available")
        return

    page_url = "https://onbeat.dance/"
    events = OnbeatEvents(page_url=page_url)
    events.parse_events()
    event_list = events.events

    if not event_list:
        print("No onbeat events found.")
        return

    print(f"Found {len(event_list)} onbeat events")

    ONBEAT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().strftime("%Y-%m-%d")
    cache_file = ONBEAT_DATA_DIR / f"{today}.json"
    
    def safe_url(val):
        return str(val) if val else None
    
    cache_data = {
        "scrape_date": today,
        "events": [
            {
                "id": e.id,
                "name": e.label.get("sv", "") if e.label else "",
                "location": e.location or "",
                "start_timestamp": e.start_timestamp.isoformat() if e.start_timestamp else None,
                "end_timestamp": e.end_timestamp.isoformat() if e.end_timestamp else None,
                "price_normal": str(e.price_normal) if e.price_normal else None,
                "venue_qid": e.identifiers.dancedatabase.venue if e.identifiers and e.identifiers.dancedatabase else "",
                "organizer_qid": e.identifiers.dancedatabase.organizer if e.identifiers and e.identifiers.dancedatabase else "",
                "dance_styles": e.identifiers.dancedatabase.dance_styles if e.identifiers and e.identifiers.dancedatabase else [],
                "links": safe_url(e.links.official_website) if e.links else None,
            }
            for e in event_list
        ]
    }
    
    with open(cache_file, "w") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)
    print(f"Cached to {cache_file}")

    if dry_run:
        print("\nDry run complete. Run without --dry-run to upload.")
        return

    client = DancedbClient()
    uploaded = 0
    skipped = 0

    try:
        for i, event in enumerate(event_list, start=1):
            label = event.label.get("sv", "Untitled") if event.label else "Untitled"
            venue = event.location or ""

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
    except Exception:
        print("\nNon-interactive mode detected. Use upload-onbeat command to upload events.")
        skipped = len(event_list)

    print(f"\nDone! {len(event_list)} events parsed, {skipped} skipped.")