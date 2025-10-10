import logging
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
import json

from models.dance_event import DanceEvent, Identifiers, DanceDatabaseIdentifiers, Organizer

CET = timezone(timedelta(hours=1))
logger = logging.getLogger(__name__)


class Dansgladje(BaseModel):
    folder: Path
    base_url: str = "https://dans.se"
    calendar_url: str = Field(default="https://dans.se/tools/calendar/?org=dansgladje&restrict=dansgladje")
    event_links: List[str] = Field(default_factory=list)

    # iCal attributes
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    description: Optional[str] = None

    # store all events
    events: List[DanceEvent] = Field(default_factory=list)

    # === Utility ===
    def clean_text(self, text: Optional[str]) -> str:
        if not text:
            return ""
        return text.replace("\xa0", " ").replace(" ", " ").strip()

    # === Calendar methods ===
    def fetch_calendar_page(self) -> str:
        resp = requests.get(self.calendar_url)
        resp.raise_for_status()
        return resp.text

    def parse_calendar_links(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        links = set()
        for selector in ["td.date a", "td.headline a"]:
            links.update(a["href"] for a in soup.select(selector) if a.get("href"))
        self.event_links = list(links)
        return self.event_links

    # === Event methods ===
    def fetch_event_page(self, url: str) -> str:
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.text

    def extract_event_metadata(self, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        label_sv = self.clean_text(soup.select_one("h1").text if soup.select_one("h1") else "")

        ical_tag = soup.select_one("a.cwIconCal")
        ical_url = ical_tag["href"] if ical_tag else None
        return {
            "label_sv": label_sv,
            "ical_url": ical_url
        }

    # === iCal methods ===
    def fetch_ical(self, ical_url: str) -> str:
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

    @staticmethod
    def map_venue_qid(description: str) -> str:
        venue_qid_map = {
            "Galaxy i Vallentuna": "Q19",
            "Sägnernas Hus": "Q21",
            "Sala Folkets Park": "Q22",
        }
        return next((qid for key, qid in venue_qid_map.items() if key in description), "")

    def check_registration(self, event_url: str) -> bool:
        """Fetch the shop page to determine if registration is open."""
        event_id = event_url.split("/")[-1]
        shop_url = f"{self.base_url}/dansgladje/shop/?event={event_id}&info=1"
        resp = requests.get(shop_url)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        registration_open = bool(soup.select("input[value='Book »']"))

        logger.debug(f"{shop_url} registration_open: {registration_open}")
        return registration_open

    # === Event workflow ===
    def fetch_event_data(self, url: str):
        page_html = self.fetch_event_page(url)
        metadata = self.extract_event_metadata(page_html)

        if not metadata["ical_url"]:
            event = {
                "id": url.split("/")[-1],
                "label": {"sv": metadata["label_sv"]},
                "registration_open": metadata["registration_open"],
                "official_website": url,
            }
            self.events.append(event)
            return

        ical_text = self.fetch_ical(metadata["ical_url"])
        self.parse_ical_text(ical_text)
        venue_qid = self.map_venue_qid(self.description)
        now = datetime.now().replace(microsecond=0).isoformat()

        event = DanceEvent(
            id=url.split("/")[-1],
            label={"sv": metadata["label_sv"]},
            description={"sv": self.description},
            start_time=self.start_time,
            end_time=self.end_time,
            location=self.location or "",
            registration_open=self.check_registration(url),
            last_update=now,
            identifiers=Identifiers(
                dancedatabase=DanceDatabaseIdentifiers(
                    venue=venue_qid,
                    dance_style="Q23",
                    organizer="Q24",
                )
            ),
            organizer=Organizer(
                description="Dansglädje",
                official_website="https://dansgladje.nu",
            ),
        )
        self.events.append(event)

    # === Export ===
    def export_to_json(self):
        Path(self.folder).mkdir(parents=True, exist_ok=True)
        file_path = Path(self.folder) / f"{self.__class__.__name__.lower()}.json"
        # Convert each Pydantic model to a plain dict
        data = [event.model_dump(mode="json") for event in self.events]

        # Serialize to JSON (Pydantic already handles datetimes nicely)
        json_data = json.dumps(data, indent=2, ensure_ascii=False)

        file_path.write_text(json_data, encoding="utf-8")
        print(f"Exported {len(self.events)} events to {file_path}")

    # === Start method ===
    def start(self):
        """Fetch all events and export them."""
        print("Fetching calendar links...")
        self.fetch_calendar_page()
        self.parse_calendar_links(self.fetch_calendar_page())

        print(f"Found {len(self.event_links)} event links. Fetching events...")
        for url in self.event_links:
            self.fetch_event_data(url)

        print("Exporting events to JSON...")
        self.export_to_json()
