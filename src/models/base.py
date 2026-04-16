"""Base classes for data sources."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class DataSource(ABC):
    """Abstract base class for data sources."""

    name: str

    @abstractmethod
    def scrape(self, **kwargs) -> list[dict[str, Any]]:
        """Scrape events from the data source."""
        pass

    @abstractmethod
    def upload(self, events: list[dict[str, Any]], **kwargs) -> int:
        """Upload events to DanceDB. Returns number of uploaded events."""
        pass


class VenueSource(ABC):
    """Abstract base class for venue sources."""

    name: str

    @abstractmethod
    def scrape_venues(self, **kwargs) -> list[dict[str, Any]]:
        """Scrape venues from the source."""
        pass

    @abstractmethod
    def match_venues(self, venues: list[dict[str, Any]], **kwargs) -> list[dict[str, Any]]:
        """Match venues to DanceDB. Returns matched venues."""
        pass
