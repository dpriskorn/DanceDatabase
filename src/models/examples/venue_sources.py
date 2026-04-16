"""Example: implementing a VenueSource for Bygdegardarna."""

from src.models.base import VenueSource


class BygdegardarnaSource(VenueSource):
    """Bygdegardarna venue source."""

    name = "bygdegardarna"

    def scrape_venues(self, **kwargs) -> list[dict]:
        """Scrape venues from bygdegardarna.se."""
        from src.models.bygdegardarna.scrape import scrape
        return scrape()

    def match_venues(self, venues: list[dict], **kwargs) -> list[dict]:
        """Match venues to DanceDB (requires DanceDB client)."""
        return venues


# Alternative implementation with data_dir:
class FolketshusSource(VenueSource):
    """Folketshus venue source."""

    name = "folketshus"

    def __init__(self, data_dir: str | None = None):
        import config
        self.data_dir = config.folketshus_dir if data_dir is None else data_dir

    def scrape_venues(self, **kwargs) -> list[dict]:
        """Scrape venues from folketshus.se."""
        from src.models.folketshus.venue import fetch_members
        return [v.model_dump() for v in fetch_members()]

    def match_venues(self, venues: list[dict], **kwargs) -> list[dict]:
        """Match venues to DanceDB."""
        from src.models.folketshus.venue import match_venues
        from src.models.folketshus.venue import FolketshusVenue
        folketshus_venues = [FolketshusVenue(**v) for v in venues]
        enriched, unmatched = match_venues(folketshus_venues)
        return enriched