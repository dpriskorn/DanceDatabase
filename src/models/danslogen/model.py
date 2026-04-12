import logging
import sys
from datetime import datetime, timedelta
from typing import List, Optional

import questionary
import requests
from bs4 import BeautifulSoup, Tag
from pydantic import AnyUrl

from src.models.danslogen.event import DanslogenEvent
from src.models.danslogen.maps import BAND_QID_MAP, VENUE_QID_MAP, fuzzy_match_qid
from src.models.danslogen.table_row import DanslogenTableRow

sys.path.insert(0, str(__file__).rsplit('/', 1)[0] + '/../../')

from config import CET
from src.models.dance_event import (
    DanceEvent,
    EventLinks,
    Identifiers,
    DanceDatabaseIdentifiers,
    Organizer,
    Registration,
)
from src.models.dancedb_client import DancedbClient

logger = logging.getLogger(__name__)


class Danslogen:
    baseurl: str = "https://www.danslogen.se"
    event_class: type[DanslogenEvent] = DanslogenEvent

    def __init__(self, month: str = "april", interactive: bool = True):
        self.month = month.lower()
        self.events: List[DanceEvent] = []
        self.dancedb_client = DancedbClient()
        self.interactive = interactive

    def fetch_month(self, month: str) -> None:
        url = f"{self.baseurl}/dansprogram/{month}"
        response = requests.get(url)
        response.raise_for_status()
        self.soup = BeautifulSoup(response.text, "lxml")
        logger.info("Fetched page: %s", url)

    def map_band_qid(self, band_name: str) -> Optional[str]:
        try:
            exact = next((qid for key, qid in BAND_QID_MAP.items()
                         if key.lower() == band_name.lower()), None)
            if exact:
                return exact
        except Exception as e:
            logger.warning("Error looking up band '%s' in band_qid_map: %s", band_name, e)
            return None

        fuzzy = fuzzy_match_qid(band_name, BAND_QID_MAP)
        if fuzzy:
            matched_key, qid, score = fuzzy
            logger.info("Fuzzy matched band '%s' to '%s' (score=%d)", band_name, matched_key, score)
            BAND_QID_MAP[band_name] = qid
            return qid
        return None

    def map_venue_qid(self, venue_name: str) -> Optional[str]:
        exact_match = next((qid for key, qid in VENUE_QID_MAP.items()
                           if key.lower() in venue_name.lower()), None)
        if exact_match:
            return exact_match
        fuzzy_result = fuzzy_match_qid(venue_name, VENUE_QID_MAP)
        if fuzzy_result:
            matched_key, qid, score = fuzzy_result
            logger.info("Fuzzy matched '%s' to '%s' (score=%d)", venue_name, matched_key, score)
            return qid
        return None

    def add_venue_qid(self, venue_name: str, qid: str) -> None:
        VENUE_QID_MAP[venue_name] = qid
        logger.info("Added venue mapping: %s -> %s", venue_name, qid)

    def parse_weekday_day(self, text: str) -> tuple[str, str]:
        parts = text.split(maxsplit=1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return text, ""

    def parse_time_range(self, time_str: str) -> tuple[str, str]:
        if not time_str or time_str.strip() == "":
            return "", ""
        if "-" in time_str:
            start, end = time_str.split("-", 1)
            return start.strip(), end.strip()
        return time_str.strip(), ""

    def parse_date(self, day: str, month: str, year: int = 2026) -> Optional[datetime]:
        try:
            month_map = {
                "januari": 1, "februari": 2, "mars": 3, "april": 4,
                "maj": 5, "juni": 6, "juli": 7, "augusti": 8,
                "september": 9, "oktober": 10, "november": 11, "december": 12
            }
            month_num = month_map.get(month.lower(), 1)
            return datetime.strptime(f"{year}-{month_num:02d}-{int(day):02d}", "%Y-%m-%d").replace(tzinfo=CET)
        except Exception as e:
            logger.warning("Failed to parse date %s %s: %s", day, month, e)
            return None

    def parse_row(self, row: Tag, month: str) -> Optional[DanceEvent]:
        try:
            table_row = DanslogenTableRow.from_row(row)
        except ValueError:
            logger.debug("Skipping invalid row")
            return None

        if not table_row:
            return None

        logger.debug("Parsed row: %s", table_row.model_dump())

        weekday = table_row.weekday
        day = table_row.day
        time_text = table_row.time
        band = table_row.band
        venue = table_row.venue or table_row.ort
        ort = table_row.ort
        kommun = table_row.kommun
        lan = table_row.lan
        ovrigt = table_row.ovrigt

        start_time, end_time = self.parse_time_range(time_text)

        band_qid = self.map_band_qid(band)
        if not band_qid:
            if not self.interactive:
                logger.debug("Band '%s' not found, skipping event (non-interactive)", band)
                return None
            try:
                band_qid = self.dancedb_client.get_or_create_band(band)
            except KeyboardInterrupt:
                logger.info("Aborted by user, exiting...")
                sys.exit(0)
            except Exception as e:
                logger.warning("Could not get/create band '%s': %s. Skipping event.", band, e)
                return None
            if band_qid:
                BAND_QID_MAP[band] = band_qid
                logger.info("Added band mapping: %s -> %s", band, band_qid)

        venue_qid = self.map_venue_qid(venue)
        if not venue_qid:
            if not self.interactive:
                logger.debug("Venue '%s' not found, skipping event (non-interactive)", venue)
                return None
            if venue == ort or not ort:
                venue_full = venue
            else:
                venue_full = f"{venue}, {ort}"
            try:
                new_qid = questionary.text(f"Unknown venue: '{venue_full}'\nEnter new QID for venue (or 'skip' to skip event)").ask()
            except KeyboardInterrupt:
                logger.info("Aborted by user, exiting...")
                sys.exit(0)
            if new_qid.lower() == 'skip':
                logger.warning("Skipping event with unknown venue: %s", venue_full)
                return None
            venue_qid = new_qid
            VENUE_QID_MAP[venue] = venue_qid
            logger.info("Added venue mapping: %s -> %s", venue, venue_qid)

        date = self.parse_date(day, month)
        if not date:
            return None

        start_dt = None
        end_dt = None
        if date and start_time:
            try:
                start_time_clean = start_time.replace('.', ':').replace('24:00', '00:00')
                start_dt = datetime.strptime(f"{date.strftime('%Y-%m-%d')} {start_time_clean}", "%Y-%m-%d %H:%M").replace(tzinfo=CET)
                if start_time_clean != start_time:
                    start_dt = start_dt + timedelta(days=1)
                if end_time:
                    end_time_clean = end_time.replace('.', ':').replace('24:00', '00:00')
                    end_dt = datetime.strptime(f"{date.strftime('%Y-%m-%d')} {end_time_clean}", "%Y-%m-%d %H:%M").replace(tzinfo=CET)
                    if end_time != end_time_clean and '24:00' in end_time:
                        end_dt = end_dt + timedelta(days=1)
            except Exception as e:
                logger.warning("Failed to parse datetime: %s", e)

        organizer = Organizer(
            description="Danslogen",
            official_website=f"{self.baseurl}/dansprogram/{month}",
        )

        event_id = f"danslogen-{month}-{day}-{band.lower().replace(' ', '-')}"

        dance_event = DanceEvent(
            id=event_id,
            label={"sv": f"{band} på {venue}"},
            description={"sv": ovrigt},
            location=venue,
            start_timestamp=start_dt,
            end_timestamp=end_dt,
            schedule={},
            price_normal=0,
            event_type="dance",
            price_reduced=None,
            links=EventLinks(
                official_website=AnyUrl(f"{self.baseurl}/dansprogram/{month}"),
                sources=[AnyUrl(f"{self.baseurl}/dansprogram/{month}")]
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
        return dance_event

    def parse_month(self, month: str) -> List[DanceEvent]:
        self.fetch_month(month)
        events: List[DanceEvent] = []

        table = self.soup.find("table", class_="danceprogram")
        if not table:
            logger.warning("No danceprogram table found for month: %s", month)
            return events

        rows = table.select("tr[class^='r']")
        logger.info("Found %d rows for month %s", len(rows), month)

        for row in rows:
            try:
                event = self.parse_row(row, month)
                if event:
                    events.append(event)
            except Exception as e:
                logger.warning("Failed to parse row: %s (type: %s)", e, type(e).__name__)
                continue

        logger.info("Parsed %d events for %s", len(events), month)
        return events

    def scrape_month(self, month: str = "april") -> List[DanceEvent]:
        self.events = self.parse_month(month)
        return self.events


def scrape_month(month: str = "april") -> List[DanceEvent]:
    scraper = Danslogen(month)
    return scraper.scrape_month(month)
