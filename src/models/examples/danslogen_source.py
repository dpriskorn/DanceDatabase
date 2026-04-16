"""Example: implementing a DataSource for Danslogen."""

from src.models.base import DataSource


class DanslogenSource(DataSource):
    """Danslogen event source."""

    name = "danslogen"

    def scrape(self, month: str = "april", year: int = 2026) -> list[dict]:
        """Scrape events from danslogen.se."""
        from src.models.danslogen.main import Danslogen

        d = Danslogen(month=month, interactive=False)
        events = d.scrape_month(month)
        return [e.model_dump(mode="json") for e in events]

    def upload(self, events: list[dict], **kwargs) -> int:
        """Upload events to DanceDB."""
        from src.models.danslogen.events.scrape import upload_events

        upload_events(input_file="", limit=kwargs.get("limit"))
        return len(events)