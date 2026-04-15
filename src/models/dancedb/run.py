import json
import logging
import sys
from datetime import date

from rapidfuzz import process as fuzz_process

from src.models.dancedb.client import DancedbClient
from src.models.dancedb.ensure_events import configure_wbi, fetch_events_from_dancedb, EVENTS_DIR, ARTISTS_DIR, \
    fetch_existing_venues

logger = logging.getLogger(__name__)


def sync_artist_spelplan(dry_run: bool = False) -> None:
    """Sync spelplan_id from danslogen data to DanceDB artists (P46).
    
    Matches artists from danslogen artists data with DanceDB artists and updates missing P46 values.
    """
    from src.models.danslogen.data import load_danslogen_artists

    configure_wbi()
    client = DancedbClient()

    danslogen_artists = load_danslogen_artists()
    if not danslogen_artists:
        logger.warning("No danslogen artists found, skipping spelplan sync")
        return

    print("\n=== Sync artist spelplan IDs ===")
    print(f"Loaded {len(danslogen_artists)} danslogen artists")

    db_artists = client.fetch_artists_from_dancedb()
    print(f"Loaded {len(db_artists)} DanceDB artists")

    updated = 0
    skipped = 0

    for artist in db_artists:
        qid = artist.get("qid", "")
        label = artist.get("label", "")
        existing_p46 = artist.get("p46", "")

        if not label:
            continue

        danslogen = danslogen_artists.get(label.lower(), {})
        spelplan_id = danslogen.get("spelplan_id", "")

        if not spelplan_id:
            continue

        if existing_p46:
            skipped += 1
            continue

        print(f"\n[{qid}] {label}")
        print(f"  Adding P46: {spelplan_id}")

        if not dry_run:
            client.set_artist_spelplan(qid, spelplan_id)
            updated += 1
        else:
            print("  (dry run - would add)")

    print("\n=== Summary ===")
    print(f"Updated: {updated}")
    print(f"Skipped (already has P46 or no spelplan_id): {skipped}")


def run(month: str = "april", year: int = 2026, dry_run: bool = False, save: bool = False) -> list[dict]:
    """Ensure all event venues exist in DanceDB.

    Returns list of events fetched from DanceDB.
    Always saves events and artists to JSON files.
    """
    configure_wbi()

    print(f"\n=== Ensuring event venues exist for {month} {year} ===")

    events = fetch_events_from_dancedb()
    print(f"Found {len(events)} events in DanceDB")

    EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = date.today().strftime("%Y-%m-%d")
    output_file = EVENTS_DIR / f"{date_str}.json"
    output_file.write_text(json.dumps(events, indent=2, ensure_ascii=False) + "\n")
    print(f"Saved to {output_file}")

    client = DancedbClient()
    artists = client.fetch_artists_from_dancedb()
    print(f"Found {len(artists)} artists in DanceDB")

    ARTISTS_DIR.mkdir(parents=True, exist_ok=True)
    artists_file = ARTISTS_DIR / f"{date_str}.json"
    artists_file.write_text(json.dumps(artists, indent=2, ensure_ascii=False) + "\n")
    print(f"Saved to {artists_file}")

    if save:
        return events

    missing_p7 = []
    venues_needed = {}

    for event in events:
        venue_qid = event.get("venue_qid")
        if not venue_qid:
            missing_p7.append(event["label"])
        else:
            venue_label = event.get("venue_label", "")
            venue_aliases = event.get("venue_aliases", [])
            venue_lower = venue_label.lower()
            if venue_lower in venues_needed:
                if venue_aliases:
                    venues_needed[venue_lower].setdefault("aliases", []).extend(venue_aliases)
            else:
                venues_needed[venue_lower] = {
                    "qid": venue_qid,
                    "label": venue_label,
                    "events": event.get("event_label", ""),
                    "aliases": venue_aliases,
                }

    if missing_p7:
        print(f"\n=== Events missing P7 ({len(missing_p7)}) ===")
        for e in missing_p7:
            print(f"  - {e}")
        print("\nABORTING: All events must have a venue (P7)")
        sys.exit(1)

    print(f"Need venues for {len(venues_needed)} unique locations")

    existing_venues = fetch_existing_venues()
    print(f"Found {len(existing_venues)} existing venues in DanceDB")

    existing_labels = list(existing_venues.keys())
    missing = []

    for venue_lower, venue_info in venues_needed.items():
        if venue_lower in existing_venues:
            continue

        # Check existing venues by aliases
        alias_match = any(
            venue_lower in v.get("aliases", [])
            for v in existing_venues.values()
        )
        if alias_match:
            continue

        # Check event venue aliases
        venue_aliases = venue_info.get("aliases", [])
        if venue_aliases:
            for v in existing_venues.values():
                existing_aliases = v.get("aliases", [])
                if any(a in existing_aliases for a in venue_aliases):
                    alias_match = True
                    break
        if alias_match:
            continue

        fuzzy = fuzz_process.extractOne(venue_lower, existing_labels, score_cutoff=90)
        if fuzzy:
            logger.info(f"Fuzzy matched '{venue_info['label']}' to '{fuzzy[0]}' ({fuzzy[1]}%)")
            continue

        missing.append(venue_info["label"])

    if missing:
        print(f"\n=== Missing venues ({len(missing)}) ===")
        for v in missing:
            print(f"  - {v}")
        year_month = f"{year}-{month[:3].title()}-01"
        print(f"\nRun 'python cli.py ensure-venues -d {year_month}' first to create missing venues.")
        sys.exit(1)

    print(f"\nAll {len(venues_needed)} venues exist in DanceDB.")
