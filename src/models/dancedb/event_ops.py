"""Event operations: scrape danslogen, upload events."""
import logging
import sys
from pathlib import Path

import questionary

from src.models.dancedb.config import config
from src.models.dancedb.status import detect_event_status
from src.models.dancedb_client import DancedbClient
from src.models.danslogen.uploader import DanslogenUploader

logger = logging.getLogger(__name__)


def scrape_danslogen(month: str = "april", year: int = 2026) -> None:
    """Fetch raw event rows from danslogen.se (no venue mapping)."""
    import json
    import requests
    from bs4 import BeautifulSoup

    print(f"\n=== Scrape danslogen events for {month} {year} ===")

    url = f"https://www.danslogen.se/dansprogram/{month}"
    print(f"Fetching: {url}")
    
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")

    rows = []
    tables = soup.find_all("table")
    for table in tables:
        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if len(cells) >= 5:
                row = {
                    "weekday": cells[0] if len(cells) > 0 else "",
                    "day": cells[1] if len(cells) > 1 else "",
                    "time": cells[2] if len(cells) > 2 else "",
                    "band": cells[3] if len(cells) > 3 else "",
                    "venue": cells[4] if len(cells) > 4 else "",
                    "ort": "",
                    "kommun": "",
                    "lan": "",
                    "ovrigt": "",
                }
                rows.append(row)

    print(f"Found {len(rows)} rows")

    output_file = f"data/danslogen_rows_{year}_{month}.json"
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    print(f"Saved to {output_file}")


def upload_events(
    input_file: str = "data/danslogen_rows_2026_april.json",
    date_str: str | None = None,
    month: str = "april",
    dry_run: bool = False,
    limit: int | None = None,
) -> None:
    """Upload danslogen events to DanceDB."""
    print(f"\n=== Upload danslogen events ===")

    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_file}")
        return

    uploader = DanslogenUploader(
        filename=input_file,
        date_str=date_str,
        month=month,
        limit=limit,
    )

    processed, events, skipped = uploader.run(dry_run=dry_run)

    if dry_run:
        print("\nDry run complete. Run without --dry-run to upload.")
        return

    if not events:
        print("No events to upload.")
        return

    client = DancedbClient()
    uploaded = 0
    skip_count = 0

    for i, event in enumerate(events, start=1):
        label = event.label.get("sv", "Untitled")
        venue_qid = event.identifiers.dancedatabase.venue
        start_ts = event.start_timestamp
        end_ts = event.end_timestamp

        print(f"\n[{i}/{len(events)}] {label}")
        print(f"  Venue: {venue_qid}")
        print(f"  Start: {start_ts}")
        print(f"  End: {end_ts}")

        confirm = questionary.rawselect(
            "Upload to DanceDB?",
            choices=["Yes (Recommended)", "Skip", "Skip all", "Abort"]
        ).ask()

        if confirm == "Skip":
            skip_count += 1
            continue
        elif confirm == "Skip all":
            print(f"Skipping remaining {len(events) - i} events...")
            skip_count += len(events) - i
            break
        elif confirm == "Abort":
            print("Aborting...")
            sys.exit(0)

        try:
            desc = event.description.get("sv", "") if event.description else ""
            search_text = f"{label} {desc}"
            status_qid, _ = detect_event_status(search_text)

            qid = client.create_event(
                label_sv=label,
                venue_qid=venue_qid,
                start_timestamp=start_ts,
                end_timestamp=end_ts,
                status_qid=status_qid,
            )
            if qid:
                print(f"  Uploaded: https://dance.wikibase.cloud/wiki/Item:{qid}")
                uploaded += 1
        except Exception as e:
            logger.error(f"Error uploading event: {e}")
            skip_count += 1

    print(f"\nDone! Uploaded {uploaded} events, {skip_count} skipped.")