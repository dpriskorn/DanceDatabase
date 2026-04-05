#!/usr/bin/env python3
"""
Upload Danslogen scraped data to DanceDB.

Reads from data/danslogen_rows_2026_april.json, processes bands and venues,
and uploads events to DanceDB via DancedbClient.
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from decimal import Decimal

import click

sys.path.insert(0, str(__file__).rsplit('/', 1)[0])

from config import CET
from pydantic import AnyUrl, TypeAdapter
from src.models.dance_event import DanceEvent, EventLinks, Identifiers, DanceDatabaseIdentifiers, Organizer, Registration
from src.models.dancedb_client import DancedbClient
from src.models.danslogen.maps import BAND_QID_MAP, VENUE_QID_MAP, fuzzy_match_qid
from src.models.danslogen.model import Danslogen

AnyUrlAdapter = TypeAdapter(AnyUrl)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def map_band_qid(band_name: str, client: DancedbClient | None = None) -> str | None:
    """Map band name to QID, creating new entry if needed."""
    exact = next((qid for key, qid in BAND_QID_MAP.items()
                  if key.lower() == band_name.lower()), None)
    if exact:
        return exact

    fuzzy = fuzzy_match_qid(band_name, BAND_QID_MAP)
    if fuzzy:
        matched_key, qid, score = fuzzy
        logger.info("Fuzzy matched band '%s' to '%s' (score=%d)", band_name, matched_key, score)
        BAND_QID_MAP[band_name] = qid
        return qid

    if client is None:
        return None

    try:
        qid = client.get_or_create_band(band_name)
        if qid:
            BAND_QID_MAP[band_name] = qid
            logger.info("Added band mapping: %s -> %s", band_name, qid)
        return qid
    except KeyboardInterrupt:
        raise
    except Exception as e:
        logger.warning("Could not get/create band '%s': %s", band_name, e)
        return None


def map_venue_qid(venue_name: str, ort: str = "", skip: bool = False) -> str | None:
    """Map venue name to QID using exact or fuzzy matching. Prompts if unknown."""
    if not venue_name:
        venue_name = ort

    exact = next((qid for key, qid in VENUE_QID_MAP.items()
                  if key.lower() in venue_name.lower()), None)
    if exact:
        return exact

    fuzzy = fuzzy_match_qid(venue_name, VENUE_QID_MAP)
    if fuzzy:
        matched_key, qid, score = fuzzy
        logger.info("Fuzzy matched venue '%s' to '%s' (score=%d)", venue_name, matched_key, score)
        return qid

    if skip:
        return None

    venue_full = venue_name if venue_name != ort else f"{venue_name}, {ort}" if ort else venue_name
    try:
        new_qid = click.prompt(f"Unknown venue: '{venue_full}'\nEnter new QID for venue (or 'skip' to skip event)")
    except (click.Abort, KeyboardInterrupt):
        raise KeyboardInterrupt()

    if new_qid.lower() == 'skip':
        logger.warning("Skipping event with unknown venue: %s", venue_full)
        return None

    VENUE_QID_MAP[venue_name] = new_qid
    logger.info("Added venue mapping: %s -> %s", venue_name, new_qid)
    return new_qid


def parse_row_to_event(row: dict, month: str, client: DancedbClient | None = None, skip_venue_prompts: bool = False) -> DanceEvent | None:
    """Convert a JSON row dict to a DanceEvent."""
    band = row.get('band', '')
    venue = row.get('venue', '') or row.get('ort', '')
    ort = row.get('ort', '')
    kommun = row.get('kommun', '')
    lan = row.get('lan', '')
    weekday = row.get('weekday', '')
    day = row.get('day', '')
    time_str = row.get('time', '')
    ovrigt = row.get('ovrigt', '')

    band_qid = map_band_qid(band, client)
    if not band_qid:
        logger.warning("Skipping event for band '%s' - no QID", band)
        return None

    venue_qid = map_venue_qid(venue, ort, skip=skip_venue_prompts)
    if not venue_qid:
        venue_full = venue if venue != ort else ort
        logger.warning("Skipping event - no venue QID for '%s'", venue_full)
        return None

    date = _parse_date(day, month)
    if not date:
        logger.warning("Skipping event - invalid date %s %s", day, month)
        return None

    start_dt, end_dt = _parse_datetime(date, time_str)

    event_id = f"danslogen-{month}-{day}-{band.lower().replace(' ', '-')}"

    organizer = Organizer(
        description="Danslogen",
        official_website=f"https://www.danslogen.se/dansprogram/{month}",
    )

    return DanceEvent(
        id=event_id,
        label={"sv": f"{band} på {venue}"},
        description={"sv": ovrigt},
        location=venue,
        start_timestamp=start_dt,
        end_timestamp=end_dt,
        schedule={},
        price_normal=Decimal(0),
        event_type="dance",
        price_reduced=None,
        links=EventLinks(
            official_website=AnyUrlAdapter.validate_strings(f"https://www.danslogen.se/dansprogram/{month}"),
            sources=[AnyUrlAdapter.validate_strings(f"https://www.danslogen.se/dansprogram/{month}")]
        ),
        organizer=organizer,
        registration=Registration(
            cancelled=False,
            fully_booked=False,
            registration_opens=None,
            registration_closes=None,
            advance_registration_required=False,
            registration_open=False
        ),
        identifiers=Identifiers(
            dancedatabase=DanceDatabaseIdentifiers(
                source="",
                venue=venue_qid,
                dance_styles=[],
                event_series="",
                organizer="",
                event=""
            )
        ),
        last_update=datetime.now().replace(tzinfo=CET, microsecond=0),
        price_late=None,
        price_early=None,
        coordinates=None,
        weekly_recurring=False,
        number_of_occasions=1
    )


def _parse_date(day: str, month: str, year: int = 2026) -> datetime | None:
    """Parse day and month name to datetime."""
    month_map = {
        "januari": 1, "februari": 2, "mars": 3, "april": 4,
        "maj": 5, "juni": 6, "juli": 7, "augusti": 8,
        "september": 9, "oktober": 10, "november": 11, "december": 12
    }
    try:
        month_num = month_map.get(month.lower(), 1)
        return datetime.strptime(f"{year}-{month_num:02d}-{int(day):02d}", "%Y-%m-%d").replace(tzinfo=CET)
    except Exception:
        return None


def _parse_datetime(date: datetime, time_str: str) -> tuple[datetime | None, datetime | None]:
    """Parse time string like '18.00-22.00' into start/end datetimes."""
    start_dt = None
    end_dt = None

    if time_str and date:
        try:
            time_clean = time_str.replace('.', ':')
            if '-' in time_clean:
                start_str, end_str = time_clean.split('-', 1)
                start_dt = datetime.strptime(
                    f"{date.strftime('%Y-%m-%d')} {start_str.strip()}",
                    "%Y-%m-%d %H:%M"
                ).replace(tzinfo=CET)
                end_dt = datetime.strptime(
                    f"{date.strftime('%Y-%m-%d')} {end_str.strip()}",
                    "%Y-%m-%d %H:%M"
                ).replace(tzinfo=CET)
            else:
                start_dt = datetime.strptime(
                    f"{date.strftime('%Y-%m-%d')} {time_clean.strip()}",
                    "%Y-%m-%d %H:%M"
                ).replace(tzinfo=CET)
        except Exception as e:
            logger.warning("Failed to parse time '%s': %s", time_str, e)

    return start_dt, end_dt


@click.command()
@click.option('--input', '-i', 'input_file',
              default='data/danslogen_rows_2026_april.json',
              help='Input JSON file with scraped rows')
@click.option('--month', '-m', default='april',
              help='Month name for URL construction')
@click.option('--dry-run', is_flag=True, default=False,
              help='Process but do not upload to DanceDB')
@click.option('--limit', '-l', type=int, default=None,
              help='Limit number of rows to process')
def upload(input_file: str, month: str, dry_run: bool, limit: int | None):
    """
    Upload Danslogen scraped data to DanceDB.

    Reads from INPUT_FILE, processes bands and venues, and uploads events.
    Use --dry-run to test without making changes to DanceDB.
    """
    input_path = Path(input_file)
    if not input_path.exists():
        click.echo(f"Error: Input file not found: {input_file}", err=True)
        sys.exit(1)

    with open(input_path) as f:
        rows = json.load(f)

    if limit:
        rows = rows[:limit]

    click.echo(f"Processing {len(rows)} rows from {input_file}")

    if dry_run:
        click.echo("DRY RUN - no changes will be made to DanceDB")

    client = None
    if not dry_run:
        client = DancedbClient()

    events = []
    skipped = 0

    for i, row in enumerate(rows):
        try:
            event = parse_row_to_event(row, month, client, skip_venue_prompts=dry_run)
            if event:
                events.append(event)
            else:
                skipped += 1
        except Exception as e:
            logger.warning("Error processing row %d: %s", i, e)
            skipped += 1

        if (i + 1) % 50 == 0:
            click.echo(f"Processed {i + 1}/{len(rows)} rows... "
                       f"{len(events)} events, {skipped} skipped")

    click.echo(f"\nDone! Processed {len(rows)} rows -> {len(events)} events, {skipped} skipped")

    if events:
        output_file = input_path.with_suffix('.events.json')
        with open(output_file, 'w') as f:
            json.dump([e.model_dump(mode='json') for e in events], f, ensure_ascii=False, indent=2)
        click.echo(f"Wrote events to {output_file}")

    if dry_run:
        click.echo("\nDry run complete. Run without --dry-run to upload.")

    if not dry_run and events:
        click.echo("\nEvents ready for upload (uploading not yet implemented)")


if __name__ == '__main__':
    upload()
