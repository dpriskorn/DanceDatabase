from src.models.cogwork.scrape import scrape
from src.models.cogwork.upload import upload


def run(source: str | None = None, dry_run: bool = False,
        upload_only: bool = False) -> None:
    """Run scrape and optionally upload cogwork events.

    Args:
        source: Optional specific source, or None for all.
        dry_run: If True, preview only.
        upload_only: If True, skip scraping.
    """
    if not upload_only:
        scrape(source=source)
    upload(source=source, dry_run=dry_run)
