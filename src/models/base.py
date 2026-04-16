"""Base classes for data sources."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class DataSource(ABC):
    """Abstract base class for data sources."""

    name: str
    data_dir: Path | None = None

    @abstractmethod
    def scrape(self, **kwargs) -> list[dict[str, Any]]:
        """Scrape events from the data source."""
        pass

    @abstractmethod
    def upload(self, events: list[dict[str, Any]], **kwargs) -> int:
        """Upload events to DanceDB. Returns number of uploaded events."""
        pass

    def get_data_dir(self) -> Path:
        """Get the data directory for this source."""
        if self.data_dir:
            return self.data_dir
        import config
        return config.data_dir / self.name


class VenueSource(ABC):
    """Abstract base class for venue sources."""

    name: str
    data_dir: Path | None = None

    @abstractmethod
    def scrape_venues(self, **kwargs) -> list[dict[str, Any]]:
        """Scrape venues from the source."""
        pass

    @abstractmethod
    def match_venues(self, venues: list[dict[str, Any]], **kwargs) -> list[dict[str, Any]]:
        """Match venues to DanceDB. Returns matched venues."""
        pass

    def get_data_dir(self) -> Path:
        """Get the data directory for this source."""
        if self.data_dir:
            return self.data_dir
        import config
        return config.data_dir / self.name
