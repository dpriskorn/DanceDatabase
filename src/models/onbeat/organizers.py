from pathlib import Path
from typing import Optional, List

import requests
from bs4 import BeautifulSoup, Tag
from pydantic import Field, BaseModel

from src.models.dance_event import DanceEvent
from src.models.onbeat.events import OnbeatEvents
from src.models.onbeat.organizer import OnbeatCommunity
from src.models.organizer import Organizer


class OnbeatOrganizers(Organizer):
    """Scrapes the communities from Onbeat."""
    baseurl: str = "https://onbeat.dance"
    json_output_folder: Path
    title: str = ""
    link: Optional[str] = None
    image: Optional[str] = None
    events: list[DanceEvent] = Field(default_factory=list)

    def scrape_clubs(self, url: str = "https://onbeat.dance/all_communities") -> List[OnbeatCommunity]:
        """Scrape all club cards from the given URL and fetch their events."""
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        cards = soup.select("div.card.custom-card")

        clubs: List[OnbeatCommunity] = []
        for card in cards:
            club = OnbeatCommunity(json_output_folder=self.json_output_folder)
            club.parse_card(card)
            if club.link:
                # try:
                oe = OnbeatEvents(page_url=self.baseurl + club.link)
                club.events = oe.parse_events()
                # except Exception as e:
                #     print(f"⚠️ Failed to fetch events for {club.title}: {e}")
                #     exit(0)
            clubs.append(club)
        return clubs

    def start(self):
        """Fetch all events and export them."""
        print("Fetching clubs and events...")
        clubs = self.scrape_clubs()
        for club in clubs:
            print(f"{club.title} ({club.link}) -> {len(club.events)} events")

        # Stop here for debugging; remove exit(0) to continue export
        # exit(0)

        # Gather all events
        for club in clubs:
            self.events.extend(club.events)

        print("Exporting events to JSON...")
        self.export_to_json()
