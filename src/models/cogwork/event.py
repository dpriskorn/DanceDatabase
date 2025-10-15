import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from src.models.dance_event import DanceEvent, Identifiers, DanceDatabaseIdentifiers, Organizer

CET = timezone(timedelta(hours=1))
logger = logging.getLogger(__name__)


class CogworkEvent(BaseModel):
    """This class maps between an event in CogWork and DanceDatabase"""
    organizer_slug: str = Field(description="Organizer in Cogwork, e.g. 'dansgladje'")
    dance_style_qid: str
    organizer_qid: str

    # event attributes
    event_url: str = Field(description="URL for event in CogWork")
    venue_qid_map: dict[str, str] = Field(description="Mapping of place to QID in DanceDatabase")
    event_metadata: dict[str, str] = Field(default_factory=dict, description="Event metadata we need")
    event_html: str = Field(default_factory=str, description="HTML from the event page")

    # iCal attributes
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    description: Optional[str] = None

    # shop attributes
    registration_open: bool = Field(False, description="Registration status at scrape time")
    registration_opens: datetime = Field(None, description="Time for when registration opens")
    shop_html: str = Field("", description="HTML from the shop page of the event")
    occasions: int = Field(0, description="Number of occasions")
    price_normal: int = Field(0, description="Price in whole SEK")

    # result
    dance_event: DanceEvent | None = Field(None, description="This CogworkEvent as DanceEvent")

    # === Utility ===
    @staticmethod
    def clean_text(text: Optional[str]) -> str:
        if not text:
            return ""
        return text.replace("\xa0", " ").replace(" ", " ").strip()

    # === Event methods ===
    @property
    def event_id(self) -> str:
        return self.event_url.split("/")[-1]

    def fetch_event_page(self) -> None:
        resp = requests.get(self.event_url)
        resp.raise_for_status()
        self.event_html = resp.text

    def extract_event_metadata(self) -> None:
        if not self.event_html:
            raise Exception("no event_html")
        soup = BeautifulSoup(self.event_html, "lxml")
        label_sv = self.clean_text(soup.select_one("h1").text if soup.select_one("h1") else "")

        ical_tag = soup.select_one("a.cwIconCal")
        ical_url = ical_tag["href"] if ical_tag else None
        self.event_metadata = {
            "label_sv": label_sv,
            "ical_url": ical_url
        }

    # === iCal methods ===
    @staticmethod
    def fetch_ical(ical_url: str) -> str:
        resp = requests.get(ical_url)
        resp.raise_for_status()
        return resp.text

    def parse_ical_text(self, text: str):
        """Extract iCal info and store in attributes."""
        def get_value(key):
            match = re.search(rf"^{key}:(.*)$", text, re.MULTILINE)
            return match.group(1).strip() if match else ""

        dtstart = get_value("DTSTART")
        dtend = get_value("DTEND")
        self.location = get_value("LOCATION")
        self.description = self.clean_text(get_value("DESCRIPTION"))

        def parse_datetime(raw):
            if not raw:
                return None
            fmt = "%Y%m%dT%H%M%S" if "T" in raw else "%Y%m%d"
            try:
                return datetime.strptime(raw.strip(), fmt).replace(tzinfo=CET)
            except ValueError:
                return None

        self.start_time = parse_datetime(dtstart)
        self.end_time = parse_datetime(dtend)

    def map_venue_qid(self, description: str) -> str:
        return next((qid for key, qid in self.venue_qid_map.items() if key in description), "")

    # === Shop methods ===
    @property
    def shop_url(self) -> str:
        """URL for shop item in CogWork"""
        return f"https://dans.se/{self.organizer_slug}/shop/?event={self.event_id}"

    def fetch_shop_page(self) -> None:
        """Fetch and store the HTML content of the shop page for the current event."""
        resp = requests.get(self.shop_url)
        resp.raise_for_status()
        self.shop_html = resp.text  # store for later use
        logger.debug(f"Fetched shop page: {self.shop_url}")

    def check_registration(self) -> None:
        """Check if registration is open for the current event."""
        if not self.shop_html:
            self.fetch_shop_page()
        soup = BeautifulSoup(self.shop_html, "lxml")
        self.registration_open = bool(soup.select("input[value='Book »']"))

        logger.debug(f"{self.shop_url} registration_open: {self.registration_open}")

    def parse_registration_datetime(self) -> None:
        """Parse the registration opening datetime from the shop HTML, if present."""
        if not self.shop_html:
            self.fetch_shop_page()
        soup = BeautifulSoup(self.shop_html, "lxml")

        status_elem = soup.select_one(".cwRegStatus")
        if not status_elem or "opens" not in status_elem.text.lower():
            logger.debug("No registration opening time found.")

        text = status_elem.get_text(strip=True)
        # Example: "Registration opens mon. 13/10 19:00"
        match = re.search(r"(\d{1,2})/(\d{1,2})\s+(\d{2}:\d{2})", text)
        if not match:
            logger.debug(f"Could not parse datetime from text: {text}")

        day, month, time_str = match.groups()
        # Assume current year (can be improved if year is known)
        year = datetime.now().year
        dt_str = f"{day}/{month}/{year} {time_str}"

        try:
            self.registration_opens = datetime.strptime(dt_str, "%d/%m/%Y %H:%M").replace(tzinfo=CET)
            logger.debug(f"Parsed registration datetime: {self.registration_opens.isoformat()}")
        except ValueError:
            raise Exception(f"Failed to parse datetime from: {dt_str}")

    def parse_occasions(self) -> None:
        """Parse and store the number of occasions from the shop HTML."""
        if not self.shop_html:
            self.fetch_shop_page()
        soup = BeautifulSoup(self.shop_html, "lxml")

        elem = soup.find("b", string="Occasions")
        if not elem or elem is None:
            raise Exception(f"No occasions found on {self.shop_url}")

        text = elem.parent.get_text(strip=True)
        match = re.search(r"Occasions\s*:\s*(\d+)", text)
        self.occasions = int(match.group(1)) if match else 0
        logger.debug(f"Parsed occasions: {self.occasions}")

    def parse_price(self) -> None:
        """Parse and store the price from the shop HTML."""
        if not self.shop_html:
            self.fetch_shop_page()
        soup = BeautifulSoup(self.shop_html, "lxml")

        elem = soup.find("b", string="Price")
        if not elem:
            raise Exception(f"No price found on {self.shop_url}")

        text = elem.parent.get_text(strip=True)
        match = re.search(r"Price\s*:\s*(\d+)", text)
        self.price_normal = int(match.group(1)) if match else 0
        logger.debug(f"Parsed price: {self.price_normal}")

    # === Event workflow ===
    # noinspection PyArgumentList
    def parse_into_dance_event(self):
        if not self.event_metadata["ical_url"]:
            raise Exception("No ical URL found")

        ical_text = self.fetch_ical(self.event_metadata["ical_url"])
        self.parse_ical_text(ical_text)
        venue_qid = self.map_venue_qid(self.description)
        now = datetime.now().replace(microsecond=0).isoformat()

        self.dance_event = DanceEvent(
            id=self.event_id,
            source="CogWork at http://dans.se",
            label={"sv": self.event_metadata["label_sv"]},
            description={"sv": self.description},
            start_time=self.start_time,
            end_time=self.end_time,
            location=self.location or "",
            registration_open=self.registration_open,
            registration_opens=self.registration_opens,
            price_normal=self.price_normal,
            last_update=now,
            identifiers=Identifiers(
                dancedatabase=DanceDatabaseIdentifiers(
                    venue=venue_qid,
                    dance_style=self.dance_style_qid,
                    organizer=self.organizer_qid,
                )
            ),
            organizer=Organizer(
            ),
        )

    def parse_shop_page(self):
        self.check_registration()
        self.parse_price()

    def fetch_and_parse(self):
        """Entrypoint"""
        self.fetch_event_page()
        self.extract_event_metadata()
        self.parse_shop_page()
        self.parse_into_dance_event()

