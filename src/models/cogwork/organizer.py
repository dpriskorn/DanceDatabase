import json
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from src.models.dance_event import DanceEvent
from src.models.cogwork.event import CogworkEvent


class CogworkOrganizer(BaseModel):
    """Abstract class for an organizer in CogWork"""
    organizer_slug: str = Field(description="Organizer in Cogwork, e.g. 'dansgladje'")
    event_class: CogworkEvent
    json_output_folder: Path
    base_url: str = "https://dans.se"
    event_links: List[str] = Field(default_factory=list)

    # store all events
    events: List[DanceEvent] = Field(default_factory=list)

    # === Utility ===
    @property
    def calendar_url(self) -> str:
        return f"https://dans.se/tools/calendar/?org={self.organizer_slug}&restrict={self.organizer_slug}"

    # === Calendar methods ===
    def fetch_calendar_page(self) -> str:
        resp = requests.get(self.calendar_url)
        resp.raise_for_status()
        return resp.text

    def parse_calendar_links(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, "lxml")
        links = set()
        for selector in ["td.date a", "td.headline a"]:
            links.update(a["href"] for a in soup.select(selector) if a.get("href"))
        self.event_links = list(links)
        return self.event_links

    # === Start method ===
    # noinspection PyArgumentList,PyCallingNonCallable
    def start(self):
        """Fetch all events and export them."""
        print("Fetching calendar links...")
        self.parse_calendar_links(self.fetch_calendar_page())

        print(f"Found {len(self.event_links)} event links. Fetching events...")
        for url in self.event_links:
            event = self.event_class(event_url=url, organizer_slug=self.organizer_slug)
            event.fetch_and_parse()
            # todo handle skipped event
            if event.skip:
                continue
            if event.dance_event is None:
                raise Exception("event.dance_event was None")
            self.events.append(event.dance_event)
        print("Exporting events to JSON...")
        self.export_to_json()

    # === Export ===
    def export_to_json(self):
        Path(self.json_output_folder).mkdir(parents=True, exist_ok=True)
        file_path = Path(self.json_output_folder) / f"{self.__class__.__name__.lower()}.json"
        # Convert each Pydantic model to a plain dict
        data = [event.model_dump(mode="json") for event in self.events]

        # Serialize to JSON (Pydantic already handles datetimes nicely)
        json_data = json.dumps(data, indent=2, ensure_ascii=False)

        file_path.write_text(json_data, encoding="utf-8")
        print(f"Exported {len(self.events)} events to {file_path}")
