import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

import requests
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, AnyUrl, Field

import config
from config import CET
from src.models.export.dance_event import (
    DanceEvent,
    EventLinks,
    Identifiers,
    DanceDatabaseIdentifiers,
    Registration,
    Organizer, )
from src.models._utils.datetime_utils import parse_iso_datetime, parse_datetime_with_range
from src.models.onbeat.venue_resolver import VenueResolver

logging.basicConfig(level=config.loglevel)
logger = logging.getLogger(__name__)


class OnbeatApiEvent(BaseModel):
    id: str
    name: str
    place: str
    start: str
    courselink: str
    clublink: str
    clubname: str
    course_image: str = ""
    club_image: Optional[str] = None


class OnbeatEvents(BaseModel):
    """
    Parses Onbeat club pages to extract courses and social dance events.
    """
    # todo support excluding inactive communities
    page_url: str
    baseurl: str = "https://onbeat.dance"
    community_qid_map: dict[str, str] = {"WCS Umeå": "Q16",
                                         "Salsa Sundsvall": "Q498",
                                         "WCS Piteå": "Q499",
                                         "Westie Vision": "Q477",
                                         "Valentine events": "Q500",
                                         "WCS Skellefteå": "Q503",
                                         "West Coast Nights": "inactive",  # no events so probably not active anymore
                                         "Z Dance Experience": "inactive"  # no events so probably not active anymore
                                         }
    dance_style_qid_map: dict = {
        "fox": "Q23",
        "west coast swing": "Q15",
        "modern fox": "Q23",
        "bugg": "Q485",
        "casanovas": "Q4",
        "socialdans": "Q4"
    }
    price_override_map: dict[str, Decimal] = {
        "rockthebarn": Decimal("1800"),
    }

    # Venue datasets for dynamic lookup
    _dancedb_venues: dict = {}
    _folketshus_venues: dict = {}
    _bygdegardarna_venues: list = []
    _venue_resolver: Optional["VenueResolver"] = None

    # Instance attributes to hold intermediate parsed data
    soup: Optional[BeautifulSoup] = None
    organizer_name: str = ""
    organizer_qid: str = ""
    container: Optional[Tag] = None
    cards: List[Tag] = []
    api_events: List[OnbeatApiEvent] = []
    current_api_event: Optional[OnbeatApiEvent] = None
    events: List[DanceEvent] = Field(default_factory=list, description="Parsed dance events")
    start_date: datetime | None = None
    end_date: datetime | None = None
    start_time: str = ""
    end_time: str = ""
    registration_open: bool = False
    model_config = {
        "arbitrary_types_allowed": True  # <-- allow BeautifulSoup and Tag
    }

    def _get_venue_resolver(self) -> VenueResolver:
        """Get or create VenueResolver instance."""
        if self._venue_resolver is None:
            self._venue_resolver = VenueResolver()
        return self._venue_resolver

    def lookup_venue_qid(self, venue_name: str) -> tuple[str | None, str | None]:
        return self._get_venue_resolver().lookup(venue_name)

    def get_venue_qid(self, venue_name: str) -> tuple[str, str | None]:
        return self._get_venue_resolver().resolve(venue_name)

    def fetch_page(self) -> None:
        response = requests.get(self.page_url)
        response.raise_for_status()
        self.soup = BeautifulSoup(response.text, "lxml")
        logger.info("Fetched page: %s", self.page_url)

    def fetch_events_from_api(self) -> List[OnbeatApiEvent]:
        """Fetch all events from the /explore API endpoint."""
        response = requests.post(
            f"{self.baseurl}/explore",
            json={"selectedValues": {"selectedCommunities": [], "selectedDates": []}},
            headers={"Content-Type": "application/json", "Accept": "application/json"}
        )
        response.raise_for_status()
        data = response.json()
        logger.info("Fetched %d events from API", len(data))
        return [OnbeatApiEvent(**item) for item in data]

    def fetch_event_details(self, clublink: str, courselink: str) -> BeautifulSoup:
        """Fetch an individual event detail page and return parsed soup."""
        url = f"{self.baseurl}/{clublink}/{courselink}"
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        logger.debug("Fetched event details: %s", url)
        return soup

    def map_dance_style_qids(self, text: str) -> set[str]:
        """Append all matching dance style QIDs based on text."""
        dance_styles_qids = set()
        for key, qid in self.dance_style_qid_map.items():
            if key.lower() in text.lower():
                dance_styles_qids.add(qid)
        return dance_styles_qids

    @staticmethod
    def parse_datetime(date_str: str, time_str: Optional[str] = None) -> Optional[datetime]:
        """Parse ISO date string with optional time, returns datetime with CET timezone."""
        return parse_iso_datetime(date_str, time_str)

    def parse_datetime_range(self, date_str: str, time_str: Optional[str] = None) -> None:
        """Parse date and time (including ranges like '18:00 - 19:00') into instance start_date/end_date."""
        self.start_date, self.end_date = parse_datetime_with_range(date_str, time_str)

    def parse_community_name(self) -> None:
        if not self.soup:
            self.fetch_page()
        header = self.soup.select_one("div.row.mt-3 h5 b")
        if header:
            self.organizer_name = header.get_text(strip=True)
            self.organizer_qid = self.map_community_qid(text=self.organizer_name)
            if not self.organizer_qid:
                logger.warning("Could not match organizer qid for community: %s", self.organizer_name)
            logger.debug("Parsed community name: %s", self.organizer_name)

    @staticmethod
    def parse_description(card_soup: Tag) -> str:
        desc_elem = card_soup.find("p", attrs={"style": lambda s: s and "white-space: pre-wrap" in s})
        if not desc_elem:
            return ""
        return desc_elem.get_text(strip=True, separator="\n")

    def find_cards(self) -> None:
        if not self.soup:
            self.fetch_page()
        self.container = self.soup.find("div", id=lambda x: x and x.startswith("clubCollapse-"))
        if not self.container:
            raise Exception("No container found with id starting with 'clubCollapse-'")
        self.cards = self.container.find_all(
            "div",
            class_=lambda c: c and "card" in c.split() and "custom-card" in c.split(),
        )

    def parse_time_range(self, value: str) -> None:
        """Parse a time range like '20:00 - 21:15' and store start/end hours as strings ("" if missing)."""
        if not value:
            return

        try:
            value = value.strip()
            if " - " in value:
                start_str, end_str = [t.strip() for t in value.split(" - ", 1)]
                self.start_time = start_str
                self.end_time = end_str
            else:
                self.start_time = value
        except Exception as e:
            logger.warning("Failed to parse time range: %s (%s)", value, e)

    @staticmethod
    def has_no_courses_message(card: Tag) -> bool:
        """Detect if the HTML card indicates that no courses are available."""
        msg_elem = card.find("p")

        if not msg_elem:
            return False

        text = msg_elem.get_text(strip=True).lower()
        return "no available courses" in text or "sorry" in text

    def parse_card_url(self, card: Tag) -> (str, str):
        """
        Extract the URL from the first <a> tag in a card and store it along with the slug.

        Args:
            card (Tag): BeautifulSoup Tag representing the course/event card.
        """
        if not card:
            return "", ""

        a_elem = card.find("a", href=True)
        if not a_elem:
            return "", ""

        url = a_elem["href"].strip()
        event_url = self.baseurl + url

        event_id = url.lstrip("/")  # remove leading slash
        return event_url, event_id

    def map_community_qid(self, text: str) -> str:
        return next((qid for key, qid in self.community_qid_map.items() if key.lower() in text.lower()), "")

    def parse_events(self) -> List[DanceEvent]:
        self.api_events = self.fetch_events_from_api()
        
        events: List[DanceEvent] = []

        for i, api_event in enumerate(self.api_events, start=1):
            self.current_api_event = api_event
            self.organizer_name = api_event.clubname
            self.organizer_qid = self.map_community_qid(text=self.organizer_name)
            
            logger.info(f"Processing event {i}/{len(self.api_events)}: {api_event.name}")
            
            soup = self.fetch_event_details(api_event.clublink, api_event.courselink)
            details = self._parse_event_details_from_soup(soup, api_event)
            
            if not details:
                logger.warning(f"Skipping event with no details: {api_event.name}")
                continue

            start_dt = parse_iso_datetime(details["start_date"], self.start_time)
            end_dt = parse_iso_datetime(details["end_date"], self.end_time)

            price_normal = self._extract_price(soup, api_event.name)

            dance_event_organizer = Organizer(
                description=self.organizer_name,
                official_website=self.page_url,
            )

            registration_opens_dt = self._parse_registration_opens(details.get("registration_opens", ""))
            registration = Registration(
                registration_opens=registration_opens_dt,
                registration_open=self.registration_open,
                advance_registration_required=True,
                cancelled=False,
                fully_booked=False,
                registration_closes=None
            )

            description = self._parse_description(soup)

            venue_qid, external_id = self.get_venue_qid(details["where"])
            if not venue_qid:
                logger.warning(f"Could not find venue: '{details['where']}' - skipping event")
                continue

            style_text = f"{api_event.name} {description}"
            dance_styles_qids = self.map_dance_style_qids(text=style_text)
            if not dance_styles_qids:
                logger.warning("Adding fallback dance style: WCS")
                dance_styles_qids.add("Q15")

            number_of_occasions = int(details.get("occasions", "0").strip()) if details.get("occasions") else 0
            recurring = number_of_occasions > 1

            event_url = f"{self.baseurl}/{api_event.clublink}/{api_event.courselink}"
            
            dance_event = DanceEvent(
                id=api_event.courselink,
                label={"sv": api_event.name},
                description={"sv": description},
                location=details["where"],
                start_timestamp=start_dt,
                end_timestamp=end_dt,
                schedule={},
                price_normal=price_normal,
                links=EventLinks(
                    official_website=AnyUrl(event_url),
                    sources=[AnyUrl(self.page_url)]
                ),
                organizer=dance_event_organizer,
                registration=registration,
                identifiers=Identifiers(
                    dancedatabase=DanceDatabaseIdentifiers(
                        source="Q501",
                        venue=venue_qid,
                        dance_styles=list(dance_styles_qids),
                        event_series="",
                        organizer=self.organizer_qid,
                        event=""
                    )
                ),
                last_update=datetime.now().replace(tzinfo=CET, microsecond=0),
                price_late=None,
                price_early=None,
                coordinates=None,
                weekly_recurring=recurring,
                number_of_occasions=number_of_occasions
            )
            events.append(dance_event)
            self._reset_per_event_state()

        logger.info("Parsed %d events total", len(events))
        self.events = events
        return events

    def _reset_per_event_state(self) -> None:
        """Reset state that is per-event to avoid carrying over between events."""
        self.soup = None
        self.start_time = ""
        self.end_time = ""
        self.registration_open = False
        self.start_date = None
        self.end_date = None

    def _parse_event_details_from_soup(self, soup: BeautifulSoup, api_event: OnbeatApiEvent) -> Optional[dict]:
        """Parse event details from the detail page soup."""
        details = {
            "where": api_event.place,
            "start_date": api_event.start,
            "end_date": "",
            "time": "",
            "occasions": "",
            "price": "",
            "registration_opens": "",
        }

        card_body = soup.find("div", class_="card-body")
        if not card_body:
            logger.warning("No card-body found in event page")
            return details

        for p in card_body.find_all("p"):
            b = p.find("b")
            if not b:
                continue
            span = b.find("span", class_="green-text")
            if not span:
                continue
            label = span.get_text(strip=True)
            value = b.next_sibling.strip() if b.next_sibling else ""
            if not value:
                continue

            if label == "Where":
                details["where"] = value
            elif label == "Start date":
                details["start_date"] = value
            elif label == "End date":
                details["end_date"] = value
            elif label == "Time":
                self.parse_time_range(value)
                details["time"] = value
            elif label == "Occasions":
                details["occasions"] = value
            elif label == "Registration opens":
                details["registration_opens"] = value

        logger.debug(f"Parsed details: {details}")
        return details

    def _parse_description(self, soup: BeautifulSoup) -> str:
        """Parse description from event detail page."""
        desc_elem = soup.find("p", class_="mt-5", attrs={"style": lambda s: s and "white-space: pre-wrap" in s})
        if not desc_elem:
            return ""
        text = desc_elem.get_text(strip=True)
        return text if text else ""

    def _extract_price(self, soup: BeautifulSoup, event_name: str) -> Decimal:
        """Extract price from event detail page."""
        for key, override_price in self.price_override_map.items():
            if key.lower() in event_name.lower():
                logger.debug(f"Using price override {override_price} for event {event_name}")
                return override_price

        price_container = soup.find("div", class_="mt-5")
        if not price_container:
            price_container = soup.find("div", class_=lambda c: c and "mt-5" in c.split() if c else False)

        if price_container:
            option_cards = price_container.find_all("div", class_="option-card")
            for card in option_cards:
                text = card.get_text(strip=True)
                import re
                match = re.search(r"(\d+)\s*SEK", text)
                if match:
                    price_val = Decimal(match.group(1))
                    logger.debug(f"Extracted price {price_val} for {event_name}")
                    return price_val

        logger.warning(f"Could not parse price for {event_name} - defaulting to 0")
        return Decimal(0)

    def _parse_registration_opens(self, reg_text: str) -> Optional[datetime]:
        """Parse registration opens datetime from text."""
        if not reg_text:
            return None

        try:
            if "CET" in reg_text:
                parts = reg_text.replace("CET", "").strip().split()
                if len(parts) >= 2:
                    dt_str = f"{parts[0]} {parts[1]}"
                    reg_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=CET)
                    if reg_dt < datetime.now().replace(tzinfo=CET):
                        self.registration_open = True
                    return reg_dt
            else:
                reg_dt = datetime.strptime(reg_text, "%Y-%m-%d").replace(tzinfo=CET)
                if reg_dt < datetime.now().replace(tzinfo=CET):
                    self.registration_open = True
                return reg_dt
        except Exception as e:
            logger.warning(f"Failed to parse registration opens: {reg_text} ({e})")
        return None
