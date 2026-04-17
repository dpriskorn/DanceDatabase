"""Event operations: scrape danslogen, upload events."""

import logging
import sys
from datetime import datetime, timezone as tz
from pathlib import Path

import json
import questionary
import rich
from rapidfuzz import fuzz

import config
from config import CET
from src.models.dancedb.client import DancedbClient
from src.models.dancedb.status import detect_event_status
from src.models.export.dance_event import DanceEvent

logger = logging.getLogger(__name__)


class MissingEventsFileError(Exception):
    """Raised when no DanceDB events file is found."""
    pass


def _load_existing_events(date_str: str) -> dict[str, dict]:
    """Load existing events from DanceDB for deduplication."""
    events_file = config.dancedb_dir / "events" / f"{date_str}.json"
    if not events_file.exists():
        events_files = sorted((config.dancedb_dir / "events").glob("*.json"), reverse=True)
        if events_files:
            raise MissingEventsFileError(
                f"No events file for {date_str}. Run 'scrape-dancedb-events -d {date_str}' first, "
                f"or use latest: scrape-dancedb-events"
            )
        raise MissingEventsFileError(
            f"No DanceDB events file found. Run 'scrape-dancedb-events' first."
        )

    existing_events = json.loads(events_file.read_text())
    print(f"Loaded {len(existing_events)} existing events from {events_file.name}")

    lookup: dict[str, dict] = {}
    for e in existing_events:
        venue_qid = e.get("venue_qid", "")
        start_ts = e.get("start_date", e.get("start_timestamp", ""))
        label = e.get("event_label", e.get("label", ""))
        qid = e.get("event_qid", e.get("qid", ""))
        if venue_qid and start_ts:
            key = f"{venue_qid}|{start_ts[:10]}"
            lookup[key] = {"qid": qid, "label": label}

    print(f"Loaded {len(lookup)} existing events for deduplication")
    return lookup


def _load_artists_lookup(date_str: str) -> dict[str, dict]:
    """Load artists from JSON for display."""
    artists_file = config.dancedb_artists_dir / f"{date_str}.json"
    if not artists_file.exists():
        return {}

    artists_data = json.loads(artists_file.read_text())
    lookup = {a.get("qid", ""): a for a in artists_data}
    print(f"Loaded {len(lookup)} artists for display")
    return lookup


def _load_venues_lookup(date_str: str) -> dict[str, dict]:
    """Load venues from JSON for display."""
    venues_dir = config.dancedb_venues_dir
    venues_file = venues_dir / f"{date_str}.json"
    if not venues_file.exists():
        venues_files = sorted(venues_dir.glob("*.json"), reverse=True)
        venues_file = venues_files[0] if venues_files else None

    if not venues_file or not venues_file.exists():
        return {}

    venues_data = json.loads(venues_file.read_text())
    lookup = {}
    for qid, v in venues_data.items():
        if isinstance(v, dict):
            lookup[qid] = v
        else:
            lookup[qid] = {"label": v, "qid": qid}

    print(f"Loaded {len(lookup)} venues from {venues_file.name}")
    return lookup


def _load_venue_mappings() -> dict[str, str]:
    """Load venue mappings from jsonl file."""
    venue_mappings_file = config.dancedb_dir / "venue_mappings.jsonl"
    if not venue_mappings_file.exists():
        return {}

    mappings: dict[str, str] = {}
    with open(venue_mappings_file) as f:
        for line in f:
            if line.strip():
                m = json.loads(line)
                mappings[m["venue_name"].lower()] = m["qid"]

    print(f"Loaded {len(mappings)} venue mappings from jsonl")
    return mappings


def _resolve_venue_qid(event: DanceEvent, venue_mappings: dict[str, str]) -> str:
    """Resolve venue QID from event or mappings."""
    venue_qid = event.identifiers.dancedatabase.venue if event.identifiers else None
    if not venue_qid and event.location:
        venue_qid = venue_mappings.get(event.location.lower())
    return venue_qid or ""


def _convert_timestamps(start_ts, end_ts) -> tuple[datetime | None, datetime | None]:
    """Convert datetime timestamps, check for past events."""
    start_dt: datetime | None = None
    end_dt: datetime | None = None

    if hasattr(start_ts, "year"):
        start_dt = start_ts if start_ts.tzinfo else start_ts.replace(tzinfo=CET)
        now = datetime.now(tz=CET)
        if start_dt < now:
            return None, None

    if hasattr(end_ts, "year"):
        end_dt = end_ts if end_ts.tzinfo else end_ts.replace(tzinfo=CET)

    return start_dt, end_dt


def _check_duplicate(
    existing_lookup: dict[str, dict],
    venue_qid: str,
    start_ts: str,
    label: str,
) -> tuple[bool, str]:
    """Check if event already exists in DanceDB."""
    if not existing_lookup or not start_ts:
        return False, ""

    date_key = f"{venue_qid}|{start_ts[:10]}"
    existing = existing_lookup.get(date_key)
    if not existing:
        return False, ""

    ratio = fuzz.ratio(label.lower(), existing["label"].lower())
    if ratio >= 85:
        return True, existing["qid"]

    return False, existing["label"]


def _display_event(
    index: int,
    total: int,
    label: str,
    venue_qid: str,
    start_ts: str,
    end_ts: str,
    venue_info: dict,
    artist_qid: str | None,
    artist_info: dict,
) -> None:
    """Display event info for user confirmation."""
    print(f"\n[{index}/{total}] {label}")
    venue_label = venue_info.get("label", "")
    print(f"  Venue: {venue_qid}{f' ({venue_label})' if venue_label else ''}")
    print(f"  Start: {start_ts}")
    if end_ts:
        print(f"  End: {end_ts}")
    if artist_qid:
        artist_label = artist_info.get("label", "")
        print(f"  Artist: {artist_qid}{f' ({artist_label})' if artist_label else ''}")


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
    """Upload danslogen events to DanceDB."""
    from datetime import date as dt

    from src.models.export.dance_event import DanceEvent

    print("\n=== Upload danslogen events ===")

    date_str = date_str or dt.today().strftime("%Y-%m-%d")
    if not input_file:
        input_file = str(config.danslogen_dir / "events" / f"{date_str}-{month.lower()}.json")
    input_path = Path(input_file)

    if not input_path.exists():
        print(f"Error: Input file not found: {input_file}")
        return

    events_data = json.loads(input_path.read_text())
    if limit:
        events_data = events_data[:limit]
    print(f"Loaded {len(events_data)} events from {input_file}")

    if not events_data:
        print("No events to upload.")
        return

    try:
        existing_lookup = _load_existing_events(date_str)
    except MissingEventsFileError as e:
        print(str(e))
        return
    artists_lookup = _load_artists_lookup(date_str)
    venues_lookup = _load_venues_lookup(date_str)
    venue_mappings = _load_venue_mappings()

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
        venue_qid = _resolve_venue_qid(event, venue_mappings)

        if not venue_qid:
            raise ValueError(
                f"Event {i} has no venue QID: {label} (location: {event.location}). "
                "Ensure venue is mapped in DanceDB first."
            )

        artist_qid = event.identifiers.dancedatabase.artist if event.identifiers else None
        start_ts, end_ts = _convert_timestamps(event.start_timestamp, event.end_timestamp)

        if start_ts is None:
            print(f"[{i}/{len(events_data)}] {label}")
            print(f"  SKIP (already started)")
            skip_count += 1
            continue

        start_ts_str = start_ts.strftime("+%Y-%m-%dT%H:%M:00Z")
        is_dup, dup_info = _check_duplicate(existing_lookup, venue_qid, start_ts_str, label)
        if is_dup:
            print(f"[{i}/{len(events_data)}] {label}")
            print(f"  SKIP (already exists: {dup_info})")
            skip_count += 1
            continue

        rich.print(event_dict)

        venue_info = venues_lookup.get(venue_qid, {})
        artist_info = artists_lookup.get(artist_qid, {}) if artist_qid else {}
        _display_event(i, len(events_data), label, venue_qid, start_ts, end_ts, venue_info, artist_qid, artist_info)

        confirm = questionary.select("Upload to DanceDB?", choices=["Yes (Recommended)", "Skip", "Skip all", "Abort"]).ask()

        if confirm == "Skip":
            skip_count += 1
            continue
        elif confirm == "Skip all":
            print(f"Skipping remaining {len(events_data) - i} events...")
            skip_count = len(events_data) - i
            break
        elif confirm == "Abort":
            print("Aborting...")
            sys.exit(0)

        try:
            desc = event.description.get("sv", "") if event.description else ""
            search_text = f"{label} {desc}"
            status_qid, _ = detect_event_status(search_text)
            instance_of = event.instance_of or config.DANCE_INSTANCE_EVENT
            dance_styles = event.identifiers.dancedatabase.dance_styles if event.identifiers else []

            qid = client.create_event(
                label_sv=label,
                venue_qid=venue_qid,
                start_timestamp=start_ts,
                end_timestamp=end_ts,
                status_qid=status_qid,
                instance_of=instance_of,
                artist_qid=artist_qid,
                dance_styles=dance_styles,
            )
            if qid:
                print(f"  Uploaded: https://dance.wikibase.cloud/wiki/Item:{qid}")
                uploaded += 1
        except Exception as e:
            logger.error("Error uploading event: %s", e)
            skip_count += 1

    print(f"\nDone! Uploaded {uploaded} events, {skip_count} skipped.")
