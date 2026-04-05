import logging
from typing import List, Optional

from bs4 import Tag
from pydantic import BaseModel, Field

from src.models.dance_event import DanceEvent

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class OnbeatCommunity(BaseModel):
    """Represents a community and its related events scraped from Onbeat."""
    title: str = ""
    link: Optional[str] = None
    image: Optional[str] = None
    events: List[DanceEvent] = Field(default_factory=list, description="List of DanceEvents for this club")

    def parse_card(self, card_soup: Tag) -> None:
        """Parse a single community card from the HTML snippet and update this instance."""
        title_elem = card_soup.select_one("h3.custom-card-title")
        link_elem = card_soup.select_one("a.btn.btn-rounded.btn-green")
        image_elem = card_soup.select_one("img.custom-card-img")

        self.title = title_elem.get_text(strip=True) if title_elem else ""
        self.link = link_elem["href"] if link_elem else None
        self.image = image_elem["src"] if image_elem else None

