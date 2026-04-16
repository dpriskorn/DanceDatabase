"""Sync for folketshus data source."""
def sync_folketshus() -> bool:
    """Sync folketshus venues: scrape + match."""
    from src.models.folketshus.venue import run as scrape_folketshus

    print("\n" + "=" * 50)
    print("SYNC FOLKETSHUS")
    print("=" * 50)

    scrape_folketshus(date_str=None)

    print("\n" + "=" * 50)
    print("FOLKETSHUS SYNC COMPLETE")
    print("=" * 50)
    return True
