import logging
import sys
from datetime import datetime
from typing import List, Optional

import questionary
import requests
from bs4 import BeautifulSoup, Tag
from pydantic import AnyUrl

from config import CET
from src.models.export.dance_event import (
    DanceEvent,
    EventLinks,
    Identifiers,
    DanceDatabaseIdentifiers,
    Organizer,
    Registration,
)
from src.models.dancedb.client import DancedbClient
from src.models.danslogen.band_mapper import BandMapper
from src.models.danslogen.venue_mapper import VenueMapper
from src.models.danslogen.event import DanslogenEvent
from src.models.danslogen.table_row import DanslogenTableRow
from src.models.danslogen.artist_row import DanslogenArtistRow
from src.models._utils.datetime_utils import MONTH_NUM_TO_NAME, combine_date_and_time, parse_time_range, parse_date

logger = logging.getLogger(__name__)


class Danslogen:
    baseurl: str = "https://www.danslogen.se"
    event_class: type[DanslogenEvent] = DanslogenEvent

    def __init__(self, month: Optional[str] = None, interactive: bool = True):
        now = datetime.now(tz=CET)
        if month is None:
            self.month = MONTH_NUM_TO_NAME[now.month]
        else:
            self.month = month.lower()
        self.year = now.year
        self.events: List[DanceEvent] = []
        self.dancedb_client = DancedbClient()
        self.band_mapper = BandMapper(client=self.dancedb_client)
        self.venue_mapper = VenueMapper(client=self.dancedb_client)
        self.interactive = interactive

    def parse_time_range(self, time_str: str) -> tuple[str, str]:
        return parse_time_range(time_str)

    def parse_date(self, day: str, month: str, year: int = 2026) -> Optional[datetime]:
        return parse_date(day, month, year)

    def fetch_month(self, month: str) -> None:
        url = f"{self.baseurl}/dansprogram/{month}"
        response = requests.get(url)
        response.raise_for_status()
        self.soup = BeautifulSoup(response.text, "lxml")
        logger.info("Fetched page: %s", url)

    def map_band_qid(self, band_name: str) -> Optional[str]:
        return self.band_mapper.resolve(band_name)

    def map_venue_qid(self, venue_name: str) -> Optional[str]:
        return self.venue_mapper.resolve(venue_name)

    def add_venue_qid(self, venue_name: str, qid: str) -> None:
        self.venue_mapper._venue_map[venue_name.lower()] = qid
        logger.info("Added venue mapping: %s -> %s", venue_name, qid)

    def parse_weekday_day(self, text: str) -> tuple[str, str]:
        parts = text.split(maxsplit=1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return text, ""

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

        start_time, end_time = parse_time_range(time_text)

        band_qid = self.map_band_qid(band)
        if not band_qid:
            if not self.interactive:
                logger.debug("Band '%s' not found, skipping event (non-interactive)", band)
                return None
            logger.warning("Could not resolve band '%s'. Skipping event.", band)
            return None

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
            self.venue_mapper._venue_map[venue.lower()] = venue_qid
            logger.info("Added venue mapping: %s -> %s", venue, venue_qid)

        date = parse_date(day, month)
        if not date:
            return None

        start_dt, end_dt = combine_date_and_time(date, time_text) if date and start_time else (None, None)

        organizer = Organizer(
            description="",
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

    def fetch_artists_page(self) -> None:
        url = f"{self.baseurl}/dansband/alla"
        response = requests.get(url)
        response.raise_for_status()
        self.soup = BeautifulSoup(response.text, "lxml")
        logger.info("Fetched artists page: %s", url)

    def parse_artists(self) -> List[DanslogenArtistRow]:
        table = self.soup.find("table")
        if not table:
            logger.warning("No table found on artists page")
            return []

        artists: List[DanslogenArtistRow] = []
        rows = table.select("tr[class='even'], tr[class='odd']")
        logger.info("Found %d artist rows", len(rows))

        for row in rows:
            try:
                artist = DanslogenArtistRow.from_row(row)
                if artist:
                    artists.append(artist)
            except Exception as e:
                logger.warning("Failed to parse artist row: %s", e)
                continue

        logger.info("Parsed %d artists", len(artists))
        return artists

    def scrape_artists(self) -> List[DanslogenArtistRow]:
        self.fetch_artists_page()
        return self.parse_artists()


def scrape_month(month: str = "april") -> List[DanceEvent]:
    scraper = Danslogen(month)
    return scraper.scrape_month(month)


def scrape_artists() -> List[DanslogenArtistRow]:
    scraper = Danslogen()
    return scraper.scrape_artists()
