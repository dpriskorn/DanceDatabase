"""Event operations: scrape danslogen, upload events."""

import logging
import sys

import questionary
import rich

import config
from src.models.dancedb.client import DancedbClient
from src.models.dancedb.status import detect_event_status

logger = logging.getLogger(__name__)


def scrape_danslogen(month: str = "april", year: int = 2026) -> None:
    """Fetch raw event rows from danslogen.se (no venue mapping).

    Args:
        month: Month name or "all" for all months
        year: Year to use in output filename (defaults to current year)
    """
    import json
    from datetime import date

    from src.models.danslogen.main import Danslogen

    date_str = date.today().strftime("%Y-%m-%d")

    months_to_scrape = []
    if month.lower() == "all":
        months_to_scrape = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"]
    else:
        months_to_scrape = [month.lower()]

    all_events = []
    for m in months_to_scrape:
        print(f"\n=== Scrape danslogen events for {m} {year} ===")
        d = Danslogen(month=m, interactive=False)
        events = d.scrape_month(m)
        print(f"Found {len(events)} events")
        all_events.extend(events)

    print(f"\nTotal: {len(all_events)} events")

    output_file = config.danslogen_dir / "events" / f"{date_str}-{month.lower()}.json"
    config.danslogen_dir.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump([e.model_dump(mode="json") for e in all_events], f, ensure_ascii=False, indent=2)

    print(f"Saved to {output_file}")


def upload_events(
    input_file: str = "",
    date_str: str | None = None,
    month: str = "april",
    dry_run: bool = False,
    limit: int | None = None,
) -> None:
    """Upload danslogen events to DanceDB.

    Loads existing events from data/dancedb/events/{date}.json for deduplication.
    """
    import json
    import os

    from rapidfuzz import fuzz

    from src.models.export.dance_event import DanceEvent

    print("\n=== Upload danslogen events ===")

    # Load existing events from JSON for deduplication
    from datetime import date as dt
    from pathlib import Path

    existing_events = []
    date_str = date_str or dt.today().strftime("%Y-%m-%d")
    if not input_file:
        input_file = str(config.danslogen_dir / "events" / f"{date_str}-{month.lower()}.json")
    input_path = Path(input_file)
    events_file = Path("data/dancedb/events") / f"{date_str}.json"
    if events_file.exists():
        existing_events = json.loads(events_file.read_text())
        print(f"Loaded {len(existing_events)} existing events from {events_file.name}")
    else:
        print(f"Warning: No existing events file found at {events_file}")
        print("Run 'poetry run python cli.py ensure-event-venues' first to fetch events from DanceDB")

    # Build lookup for existing events
    existing_lookup: dict[str, dict] = {}
    for e in existing_events:
        venue_qid = e.get("venue_qid", "")
        start_ts = e.get("start_date", e.get("start_timestamp", ""))
        label = e.get("event_label", e.get("label", ""))
        qid = e.get("event_qid", e.get("qid", ""))
        if venue_qid and start_ts:
            key = f"{venue_qid}|{start_ts[:10]}"
            existing_lookup[key] = {"qid": qid, "label": label}

    print(f"Loaded {len(existing_lookup)} existing events for deduplication")

    # Load artists from JSON for display
    artists_lookup: dict[str, dict] = {}
    artists_file = Path("data/dancedb/artists") / f"{date_str}.json"
    if artists_file.exists():
        artists_data = json.loads(artists_file.read_text())
        for a in artists_data:
            artists_lookup[a.get("qid", "")] = a
        print(f"Loaded {len(artists_lookup)} artists for display")

    # Load venues from JSON for display
    venues_lookup: dict[str, dict] = {}
    venues_dir = Path("data/dancedb/venues")
    venues_file = venues_dir / f"{date_str}.json"
    if not venues_file.exists():
        venues_files = sorted(venues_dir.glob("*.json"), reverse=True)
        if venues_files:
            venues_file = venues_files[0]
    if venues_file.exists():
        venues_data = json.loads(venues_file.read_text())
        for qid, v in venues_data.items():
            if isinstance(v, dict):
                venues_lookup[qid] = v
            else:
                venues_lookup[qid] = {"label": v, "qid": qid}
        print(f"Loaded {len(venues_lookup)} venues for display from {venues_file.name}")

    # Load newly created venue mappings from jsonl
    venue_mappings: dict[str, str] = {}
    venue_mappings_file = Path("data/dancedb/venue_mappings.jsonl")
    if venue_mappings_file.exists():
        with open(venue_mappings_file) as f:
            for line in f:
                if line.strip():
                    m = json.loads(line)
                    venue_mappings[m["venue_name"].lower()] = m["qid"]
        print(f"Loaded {len(venue_mappings)} venue mappings from jsonl")

    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_file}")
        return

    events_data = json.loads(input_path.read_text())
    if limit:
        events_data = events_data[:limit]
        print(f"(Limited to {limit} events)")

    print(f"Loaded {len(events_data)} events from {input_file}")

    if not events_data:
        print("No events to upload.")
        return

    client = DancedbClient()
    uploaded = 0
    skip_count = 0

    for i, event_dict in enumerate(events_data, start=1):
        try:
            event = DanceEvent.model_validate(event_dict)
        except Exception as e:
            logger.warning("Failed to parse event %d: %s", i, e)
            skip_count += 1
            continue

        label = event.label.get("sv", "Untitled") if event.label else "Untitled"
        venue_qid = event.identifiers.dancedatabase.venue if event.identifiers else None
        artist_qid = event.identifiers.dancedatabase.artist if event.identifiers else None
        start_ts = event.start_timestamp
        end_ts = event.end_timestamp
        location = event.location or ""

        if not venue_qid and location:
            venue_qid = venue_mappings.get(location.lower())
            if venue_qid:
                event.identifiers.dancedatabase.venue = venue_qid

        if not venue_qid:
            logger.warning("Skipping event %d - no venue QID", i)
            skip_count += 1
            continue

        # Check for duplicate in existing events
        if existing_lookup and start_ts:
            # Convert datetime to string if needed
            if hasattr(start_ts, "strftime"):
                start_ts = start_ts.strftime("%Y-%m-%dT%H:%M:%S")
            date_key = f"{venue_qid}|{start_ts[:10]}"
            existing = existing_lookup.get(date_key)
            if existing:
                ratio = fuzz.ratio(label.lower(), existing["label"].lower())
                if ratio >= 85:
                    print(f"\n[{i}/{len(events_data)}] {label}")
                    print(f"  SKIP (already exists: {existing['qid']})")
                    skip_count += 1
                    continue
                else:
                    print(f"\n[{i}/{len(events_data)}] {label}")
                    print(f"  WARNING: Same venue/date but different label: {existing['label']} (fuzzy match: {ratio}%)")
                    if not yes:
                        confirm = questionary.select("Event may already exist. Upload anyway?", choices=["Skip", "Upload", "Skip all", "Abort"]).ask()
                        if confirm == "Skip":
                            skip_count += 1
                            continue
                        elif confirm == "Skip all":
                            print(f"Skipping remaining {len(events_data) - i} events...")
                            skip_count += len(events_data) - i
                            break
                        elif confirm == "Abort":
                            print("Aborting...")
                            sys.exit(0)

        rich.print(event_dict)

        print(f"\n[{i}/{len(events_data)}] {label}")
        venue_info = venues_lookup.get(venue_qid, {})
        venue_label = venue_info.get("label", "")
        print(f"  Venue: {venue_qid}{f' ({venue_label})' if venue_label else ''}")
        print(f"  Start: {start_ts}")
        print(f"  End: {end_ts}")

        if artist_qid:
            artist_info = artists_lookup.get(artist_qid, {})
            artist_label = artist_info.get("label", "")
            print(f"  Artist: {artist_qid}{f' ({artist_label})' if artist_label else ''}")

        confirm = questionary.select("Upload to DanceDB?", choices=["Yes (Recommended)", "Skip", "Skip all", "Abort"]).ask()

        if confirm == "Skip":
            skip_count += 1
            continue
        elif confirm == "Skip all":
            print(f"Skipping remaining {len(events_data) - i} events...")
            skip_count += len(events_data) - i
            break
        elif confirm == "Abort":
            print("Aborting...")
            sys.exit(0)

        try:
            desc = event.description.get("sv", "") if event.description else ""
            search_text = f"{label} {desc}"
            status_qid, _ = detect_event_status(search_text)
            instance_of = event.instance_of if hasattr(event, "instance_of") else "Q2"
            artist_qid = event.identifiers.dancedatabase.artist if event.identifiers else None

            qid = client.create_event(
                label_sv=label,
                venue_qid=venue_qid,
                start_timestamp=start_ts,
                end_timestamp=end_ts,
                status_qid=status_qid,
                instance_of=instance_of,
                artist_qid=artist_qid,
            )
            if qid:
                print(f"  Uploaded: https://dance.wikibase.cloud/wiki/Item:{qid}")
                uploaded += 1
        except Exception as e:
            logger.error("Error uploading event: %s", e)
            skip_count += 1

    print(f"\nDone! Uploaded {uploaded} events, {skip_count} skipped.")
