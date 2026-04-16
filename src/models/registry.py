"""Data source registry."""
from pathlib import Path
from typing import Any

from src.models.base import DataSource, VenueSource


def discover_sources() -> dict[str, type[DataSource]]:
    """Discover all DataSource subclasses."""
    sources: dict[str, type[DataSource]] = {}
    for cls in DataSource.__subclasses__():
        sources[cls.name] = cls
    return sources


def discover_venue_sources() -> dict[str, type[VenueSource]]:
    """Discover all VenueSource subclasses."""
    sources: dict[str, type[VenueSource]] = {}
    for cls in VenueSource.__subclasses__():
        sources[cls.name] = cls
    return sources


def create_source(name: str) -> DataSource | None:
    """Create a source instance by name."""
    sources = discover_sources()
    cls = sources.get(name)
    return cls() if cls else None


def create_venue_source(name: str) -> VenueSource | None:
    """Create a venue source instance by name."""
    sources = discover_venue_sources()
    cls = sources.get(name)
    return cls() if cls else None


def list_sources() -> list[str]:
    """List all registered data source names."""
    return list(discover_sources().keys())


def list_venue_sources() -> list[str]:
    """List all registered venue source names."""
    return list(discover_venue_sources().keys())