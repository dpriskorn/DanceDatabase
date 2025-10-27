import logging
import re
from datetime import datetime
from typing import Optional, cast

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, AnyUrl

from config import CET
from src.models.dance_event import DanceEvent, Identifiers, DanceDatabaseIdentifiers, Organizer, EventLinks, \
    Registration

logger = logging.getLogger(__name__)
DANCE_STYLE_MAP = {
    "fox": "Q23",
    "west coast swing": "Q15",
    "modern fox": "Q23",
    "bugg": "Q485",
}
FULL_MAPPING = [
    "FULLT",
    "FULLBOKAD"
]


class CogworkEvent(BaseModel):
    """This class maps between an event in CogWork and DanceDatabase"""
    organizer_slug: str = Field(description="Organizer in Cogwork, e.g. 'dansgladje'")
    organizer_qid: str

    # skip
    skip_sv_labels: list[str] = Field(default_factory=list, description="Ignore events with labels matching entries in this list (case-insensitive)")
    skip: bool = Field(False, description="Skip storing this event")

    # full
    full_mapping_sv: list[str] = FULL_MAPPING
    full: bool = Field(False, description="Whether the event is fully booked")

    # mappings
    dance_style_qid_map: dict[str, str] = Field(DANCE_STYLE_MAP, description="Mapping of dance style to QID in DanceDatabase (case-insensitive)")
    venue_qid_map: dict[str, str] = Field(description="Mapping of place to QID in DanceDatabase (case-insensitive)")

    # event attributes
    event_url: str = Field(description="URL for event in CogWork")
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
    place: str = Field("", description="Place where the event happens")
    dance_styles_qids: set[str] = Field(default_factory=set, description="Dance style QIDs in DanceDatabase")

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

    def map_venue_qid(self, text: str) -> str:
        return next((qid for key, qid in self.venue_qid_map.items() if key.lower() in text.lower()), "")

    def map_dance_style_qids(self, text: str) -> None:
        """Append all matching dance style QIDs based on text."""
        for key, qid in self.dance_style_qid_map.items():
            if key.lower() in text.lower():
                self.dance_styles_qids.add(qid)

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

    def parse_place(self) -> None:
        """Parse the place from the shop HTML, if present."""
        if not self.shop_html:
            self.fetch_shop_page()
        soup = BeautifulSoup(self.shop_html, "lxml")

        # Parse place
        place_elem = soup.select_one(".cwPlace")
        if place_elem:
            self.place = place_elem.get_text(strip=True)
            logger.debug(f"Place parsed: {self.place}")
        else:
            logger.debug("No place found in HTML.")

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
            logger.warning(f"No price found on {self.shop_url}")
        else:
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
        venue_text = f"{self.place} {self.description}"
        venue_qid = self.map_venue_qid(venue_text)
        if not venue_qid:
            raise Exception(f"Could not map to a venue QID from this text: \n'{venue_text}'\nsee {self.shop_url}")
        style_text = f"{self.event_metadata["label_sv"]} {self.description}"
        self.map_dance_style_qids(text=style_text)
        if not self.dance_styles_qids:
            raise Exception(f"Could not map to any dance style QIDs from this text: \n'{style_text}'\nsee {self.shop_url}")
        now = datetime.now().replace(microsecond=0).isoformat()

        self.dance_event = DanceEvent(
            id=self.event_id,
            # source="CogWork at http://dans.se",
            label={"sv": self.event_metadata["label_sv"]},
            description={"sv": self.description},
            start_timestamp=self.start_time,
            end_timestamp=self.end_time,
            location=self.location or "",
            price_normal=self.price_normal,
            last_update=now,
            registration=Registration(
                registration_open=self.registration_open,
                registration_opens=self.registration_opens,
                advance_registration_required=True,
                fully_booked=self.full
            ),
            identifiers=Identifiers(
                dancedatabase=DanceDatabaseIdentifiers(
                    venue=venue_qid,
                    dance_styles=list(self.dance_styles_qids),
                    organizer=self.organizer_qid,
                    source="Q484",
                )
            ),
            organizer=Organizer(
            ),
            links=EventLinks(
                sources=cast(list[AnyUrl], [
                    self.event_url,
                    self.shop_url
                ])
            )
        )

    def determine_skip(self):
        label_sv = self.event_metadata["label_sv"]
        for ignore_label in self.skip_sv_labels:
            if ignore_label.lower() in label_sv.lower():
                logger.debug(f"Skipping '{label_sv}' because of match with this ignore label: '{ignore_label}'")
                self.skip = True
        logger.debug(f"Accepted: {label_sv} based on ignore list: {self.skip_sv_labels}")

    def determine_full(self):
        label_sv = self.event_metadata["label_sv"]
        for full_label in self.full_mapping_sv:
            if full_label.lower() in label_sv.lower():
                logger.debug(f"Marking '{label_sv}' as full because of match with this full label: '{full_label}'")
                self.full = True
        # logger.debug(f"Accepted: {label_sv} based on ignore list: {self.full_mapping_sv}")

    def parse_shop_page(self):
        """Parse all the data we want from the shop page"""
        self.check_registration()
        self.parse_price()
        self.parse_place()

    def fetch_and_parse(self):
        """Entrypoint"""
        self.fetch_event_page()
        self.extract_event_metadata()
        self.determine_skip()
        if not self.skip:
            self.determine_full()
            self.parse_shop_page()
            self.parse_into_dance_event()

