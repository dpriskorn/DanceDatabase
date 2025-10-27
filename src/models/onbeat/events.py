import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

import requests
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, AnyUrl, Field

import config
from config import CET
from src.models.dance_event import (
    DanceEvent,
    EventLinks,
    Identifiers,
    DanceDatabaseIdentifiers,
    Registration,
    Organizer, )

logging.basicConfig(level=config.loglevel)
logger = logging.getLogger(__name__)


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
    venue_qid_map: dict[str, str] = Field({
            "Norrfjärdens Folkets Hus": "Q502",
            "Johannesbergs Castle": "Q504",
            "Trafikgatan 54": "Q505",
            "Klemensnäs Folkets Hus": "Q122",
            "Umeå Folkets Hus": "Q17"
        },
        description="Mapping of place to QID in DanceDatabase (case-insensitive)")

    # Instance attributes to hold intermediate parsed data
    soup: Optional[BeautifulSoup] = None
    organizer_name: str = ""
    organizer_qid: str = ""
    container: Optional[Tag] = None
    cards: List[Tag] = []
    start_date: datetime | None = None
    end_date: datetime | None = None
    start_time: str = ""
    end_time: str = ""
    registration_open: bool = False
    model_config = {
        "arbitrary_types_allowed": True  # <-- allow BeautifulSoup and Tag
    }

    def fetch_page(self) -> None:
        response = requests.get(self.page_url)
        response.raise_for_status()
        self.soup = BeautifulSoup(response.text, "lxml")
        logger.info("Fetched page: %s", self.page_url)

    def map_dance_style_qids(self, text: str) -> set[str]:
        """Append all matching dance style QIDs based on text."""
        dance_styles_qids = set()
        for key, qid in self.dance_style_qid_map.items():
            if key.lower() in text.lower():
                dance_styles_qids.add(qid)
        return dance_styles_qids

    @staticmethod
    def parse_datetime(date_str: str, time_str: Optional[str] = None) -> Optional[datetime]:
        """
        Parse date and time, optionally with a timezone abbreviation (e.g., '18:00 CEST').
        Returns a datetime with tzinfo=CET.
        """
        if not date_str:
            return None

        try:
            if time_str:
                # Remove any non-numeric characters (e.g., "CEST") from time
                time_clean = time_str.split()[0]  # keeps only "HH:MM"
                dt_str = f"{date_str} {time_clean}"
                return datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=CET)
            return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=CET)
        except Exception as e:
            logger.warning("Failed to parse datetime: %s %s (%s)", date_str, time_str, e)
            return None

    def parse_datetime_range(self, date_str: str, time_str: Optional[str] = None) -> None:
        """Parse date and time (including ranges like '18:00 - 19:00') into start_time and end_time."""
        if not date_str:
            return

        try:
            if time_str and " - " in time_str:
                start_str, end_str = [t.strip() for t in time_str.split(" - ", 1)]
                self.start_date = datetime.strptime(f"{date_str} {start_str}", "%Y-%m-%d %H:%M").replace(tzinfo=CET)
                self.end_date = datetime.strptime(f"{date_str} {end_str}", "%Y-%m-%d %H:%M").replace(tzinfo=CET)
            elif time_str:
                self.start_date = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=CET)
            else:
                self.start_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=CET)
        except Exception as e:
            logger.warning("Failed to parse datetime: %s %s (%s)", date_str, time_str, e)

    def parse_community_name(self) -> None:
        if not self.soup:
            self.fetch_page()
        header = self.soup.select_one("div.row.mt-3 h5 b")
        if header:
            self.organizer_name = header.get_text(strip=True)
            self.organizer_qid = self.map_community_qid(text=self.organizer_name)
            if not self.organizer_qid:
                raise Exception("could not match organizer qid")
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

        value = value.strip()
        try:
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

    def map_venue_qid(self, text: str) -> str:
        return next((qid for key, qid in self.venue_qid_map.items() if key.lower() in text.lower()), "")

    def map_community_qid(self, text: str) -> str:
        return next((qid for key, qid in self.community_qid_map.items() if key.lower() in text.lower()), "")

    def parse_events(self) -> List[DanceEvent]:
        if not self.cards:
            self.find_cards()
        if not self.organizer_name:
            self.parse_community_name()

        events: List[DanceEvent] = []

        for i, card in enumerate(self.cards, start=1):
            if self.has_no_courses_message(card=card):
                continue
            logger.debug(f"card: \n{card}")
            title_elem = card.find("h5", class_="card-title")
            label_sv = title_elem.get_text(strip=True) if title_elem else ""
            if not label_sv:
                logger.warning(f"No label found for card {i}: {title_elem}")
                continue

            event_url, event_id = self.parse_card_url(card=card)
            details = {
                "where": "",
                "start_date": "",
                "end_date": "",
                "time": "",
                "occasions": "",
                "price": "",
                "registration_opens": "",
            }

            for p in card.find_all("p"):
                b = p.find("b")
                if not b:
                    continue
                key = b.get_text(strip=True).rstrip(":")
                value = b.next_sibling.strip() if b.next_sibling else ""
                if not value:
                    value = p.get_text(strip=True).replace(b.get_text(strip=True), "").strip()
                if key == "Where":
                    details["where"] = value
                elif key == "Start date":
                    details["start_date"] = value
                elif key == "End date":
                    details["end_date"] = value
                elif key == "Time":
                    self.parse_time_range(value)
                    details["time"] = value
                elif key == "Occasions":
                    details["occasions"] = value
                elif key == "Price":
                    details["price"] = value
                elif key == "Registration opens":
                    # logger.debug(f"value: {value}")
                    if "1970-01-01" in value:
                        details["registration_opens"] = ""
                        self.registration_open = True
                    else:
                        details["registration_opens"] = value
            logger.debug(f"Found details:\n{details}")
            start_dt = self.parse_datetime(details["start_date"], self.start_time)
            end_dt = self.parse_datetime(details["end_date"], self.end_time)

            try:
                price_normal = Decimal(details["price"].replace("SEK", "").replace("kr", "").replace(",", ".").strip())
            except Exception:
                logger.warning(f"Could not parse price '{details["price"]}' into Decimal")
                price_normal = None

            dance_event_organizer = Organizer(
                description=self.organizer_name,
                official_website=self.page_url,
            )

            if details["registration_opens"]:
                if "CEST" in details["registration_opens"]:
                    # extract time component
                    parts = details["registration_opens"].split()
                    time = parts[1]
                    date = parts[0]
                    logger.debug(f"parsing registration opens with date: {date} and time:{time}")
                    registration_opens_dt = self.parse_datetime(date, time)
                else:
                    logger.debug(f"parsing registration opens from {details["registration_opens"]}")
                    registration_opens_dt = self.parse_datetime(details["registration_opens"])
                if registration_opens_dt is not None and registration_opens_dt < datetime.now().replace(tzinfo=CET):
                    self.registration_open = True
            else:
                registration_opens_dt = None
            registration = Registration(
                registration_opens=registration_opens_dt,
                registration_open=self.registration_open,
                advance_registration_required=True,  # hardcoded because everything in the site seems to be
                cancelled=False,  # todo how do we handle this?
                fully_booked=False,  # todo how do we handle this?
                registration_closes=None  # not available
            )

            description = self.parse_description(card)

            # venue
            venue_text = f"{details["where"]} {description}"
            venue_qid = self.map_venue_qid(venue_text)
            if not venue_qid:
                raise Exception(f"Could not map to a venue QID from this text: \n'{venue_text}'\nsee {self.page_url} and {event_url}")

            # style
            style_text = f"{label_sv} {description}"
            dance_styles_qids = self.map_dance_style_qids(text=style_text)
            if not dance_styles_qids:
                # fallback to WCS
                logger.warning("Adding fallback dance style: WCS")
                dance_styles_qids.add("Q15")
                # raise Exception("could not match at least one dance style")

            # recurring
            occasions = details["occasions"]
            # print(occasions)
            number_of_occasions = 0
            if occasions:
                try:
                    number_of_occasions = int(occasions.strip())
                except TypeError:
                    raise Exception(f"could not parse '{occasions}' to int")
            if number_of_occasions > 1:
                recurring = True
            else:
                recurring = False

            dance_event = DanceEvent(
                id=event_id,
                label={"sv": label_sv},
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
            # pprint(dance_event.model_dump())
            # exit(0)
            events.append(dance_event)

        logger.info("Parsed %d events for %s", len(events), self.organizer_name)
        return events
