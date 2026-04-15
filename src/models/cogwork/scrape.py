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


def scrape(source: str | None = None, overwrite: bool = False) -> None:
    """Scrape cogwork events.

    Args:
        source: Optional specific source, or None for all.
        overwrite: If True, overwrite existing output files.
    """
    import importlib
    from datetime import date

    import config

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

    date.today().strftime("%Y-%m-%d")
    output_base = config.data_dir / "cogwork"

    for name in sources_to_scrape:
        print(f"\n--- {name} ---")
        try:
            output_folder = output_base / name
            output_folder.mkdir(parents=True, exist_ok=True)

            module = importlib.import_module(f"src.models.cogwork.scrapers.{name}")
            scraper_class = getattr(module, name.capitalize())
            scraper = scraper_class(json_output_folder=output_folder)
            scraper.start(overwrite=overwrite)
            print(f"  Done: {name}")
        except Exception as e:
            print(f"  Error: {name} - {e}")

    print(f"\nTotal: {len(sources_to_scrape)} sources configured")


