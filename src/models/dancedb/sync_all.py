"""Sync all data sources."""
import logging
import sys
from datetime import date

logger = logging.getLogger(__name__)


def scrape_all(month: str, year: int) -> None:
    """Scrape all data sources first."""
    from src.models.cogwork.scrape import scrape as scrape_cogwork
    from src.models.dancedb.scrape import scrape_bygdegardarna
    from src.models.danslogen.events.scrape import scrape_danslogen
    from src.models.folketshus.venue import run as scrape_folketshus
    from src.models.onbeat.run import run as scrape_onbeat
    from src.models.wikidata.operations import scrape_wikidata_artists

    date_str = date.today().strftime("%Y-%m-%d")
    from src.models.dancedb.sync_ops import get_data_dir
    get_data_dir()

    print("\n" + "=" * 50)
    print("SCRAPING ALL DATA SOURCES")
    print("=" * 50)

    print("\n[1/6] Scrape Wikidata artists...")
    scrape_wikidata_artists(date_str=date_str)

    print("\n[2/6] Scrape danslogen events...")
    scrape_danslogen(month=month, year=year)

    print("\n[3/6] Scrape bygdegardarna venues...")
    scrape_bygdegardarna(date_str=date_str)

    print("\n[4/6] Scrape onbeat events...")
    scrape_onbeat()

    print("\n[5/6] Scrape cogwork events...")
    scrape_cogwork(source=None)

    print("\n[6/6] Scrape folketshus venues...")
    scrape_folketshus(date_str=date_str)

    print("\n" + "=" * 50)
    print("SCRAPING COMPLETE")
    print("=" * 50)


def sync_all(
    month: str | None = None,
    year: int | None = None,
    limit: int | None = None,
    only_scrape: bool = False,
) -> bool:
    """Sync all sources with prerequisite checking."""
    from src.models.dancedb.sync_danslogen import get_current_month_year
    from src.models.dancedb.sync_bygdegardarna import sync_bygdegardarna
    from src.models.dancedb.sync_onbeat import sync_onbeat
    from src.models.dancedb.sync_cogwork import sync_cogwork
    from src.models.dancedb.sync_folketshus import sync_folketshus
    from src.models.dancedb.sync_danslogen import sync_danslogen

    if month is None or year is None:
        month, year = get_current_month_year()

    print("\n" + "=" * 60)
    print(f"SYNC ALL SOURCES: {month} {year}")
    print("=" * 60)

    print("\n[0/6] Scraping all data sources...")
    scrape_all(month=month, year=year)

    sources = [
        ("DANSLOGEN", lambda: sync_danslogen(month=month, year=year, limit=limit, only_scrape=only_scrape)),
        ("BYGDEGARDARNA", lambda: sync_bygdegardarna(only_scrape=only_scrape)),
        ("ONBEAT", lambda: sync_onbeat()),
        ("COGWORK", lambda: sync_cogwork()),
        ("FOLKETSHUS", lambda: sync_folketshus()),
    ]

    for i, (name, func) in enumerate(sources, 1):
        print(f"\n{'=' * 60}")
        print(f"SYNCING [{i}/{len(sources)}]: {name}")
        print("=" * 60)
        try:
            func()
        except Exception as e:
            logger.error(f"Failed to sync {name}: %s", e)
            print(f"\nERROR: {name} sync failed: {e}")
            print("\nAborting sync-all. Fix the error and try again.")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("ALL SOURCES SYNC COMPLETE")
    print("=" * 60)
    return True
