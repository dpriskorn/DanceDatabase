"""Sync for onbeat data source."""
def sync_onbeat() -> bool:
    """Sync onbeat events: scrape + upload."""
    from src.models.onbeat.run import run as scrape_onbeat

    print("\n" + "=" * 50)
    print("SYNC ONBEAT")
    print("=" * 50)

    scrape_onbeat()

    print("\n" + "=" * 50)
    print("ONBEAT SYNC COMPLETE")
    print("=" * 50)
    return True
