"""Cogwork scraper commands."""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_scrapers() -> dict:
    """Discover all cogwork scrapers."""
    scrapers = {}
    scraper_dir = Path(__file__).parent.parent / "cogwork" / "scrapers"

    if not scraper_dir.exists():
        return {}

    for f in scraper_dir.glob("*.py"):
        if f.stem.startswith("_"):
            continue
        module_name = f.stem
        scrapers[module_name] = module_name

    return scrapers


def scrape(source: str | None = None) -> None:
    """Scrape cogwork events.

    Args:
        source: Optional specific source, or None for all.
    """
    import importlib

    from src.models.dancedb.config import config

    print("\n=== Scrape cogwork events ===")

    scrapers = get_scrapers()
    if not scrapers:
        print("No cogwork scrapers found")
        return

    print(f"Available sources: {', '.join(sorted(scrapers.keys()))}")

    if source and source not in scrapers:
        print(f"Unknown source: {source}")
        return

    sources_to_scrape = [source] if source else list(scrapers.keys())

    print(f"\nScraping {len(sources_to_scrape)} sources...")

    output_folder = config.data_dir / "cogwork"
    output_folder.mkdir(parents=True, exist_ok=True)

    for name in sources_to_scrape:
        print(f"\n--- {name} ---")
        try:
            module = importlib.import_module(f"src.models.cogwork.scrapers.{name}")
            scraper_class = getattr(module, name.capitalize())
            scraper = scraper_class(json_output_folder=output_folder)
            scraper.start()
            print(f"  Done: {name}")
        except Exception as e:
            print(f"  Error: {name} - {e}")

    print(f"\nTotal: {len(sources_to_scrape)} sources configured")


def upload(source: str | None = None, dry_run: bool = False) -> None:
    """Upload cogwork events to DanceDB with confirmation.

    Args:
        source: Optional specific source, or None for all.
        dry_run: If True, preview only.
    """
    print("\n=== Upload cogwork events ===")

    scrapers = get_scrapers()
    if not scrapers:
        print("No cogwork scrapers found")
        return

    if dry_run:
        print("DRY RUN - no events will be uploaded")

    print(f"Available sources: {', '.join(sorted(scrapers.keys()))}")

    if source and source not in scrapers:
        print(f"Unknown source: {source}")
        return

    if dry_run:
        print("\nDry run complete. Run without --dry-run to upload.")
        return

    print("\nCogwork upload: (not fully implemented)")
    print("Use individual scrapers first, then upload via danslogen if needed")


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