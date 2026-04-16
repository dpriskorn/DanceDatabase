"""Onbeat scraper commands."""

import json
import logging
from datetime import date

import config
from src.models.onbeat.events import OnbeatEvents

logger = logging.getLogger(__name__)

ONBEAT_DATA_DIR = config.onbeat_dir


def run(dry_run: bool = False) -> None:
    """Fetch onbeat events."""
    print("\n=== Scrape onbeat events ===")

    events = OnbeatEvents(page_url="https://onbeat.dance/")
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
        ],
    }

    with open(cache_file, "w") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)
    print(f"Cached to {cache_file}")
    print(f"Found {len(event_list)} onbeat events")
    print("Run 'onbeat-ensure-venues' to create missing venues, then 'upload-onbeat' to upload.")
