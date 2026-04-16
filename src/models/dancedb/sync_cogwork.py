"""Sync for cogwork data source."""
def sync_cogwork() -> bool:
    """Sync cogwork events: scrape + upload."""
    from src.models.cogwork.scrape import scrape as scrape_cogwork
    from src.models.cogwork.upload import upload as upload_cogwork

    print("\n" + "=" * 50)
    print("SYNC COGWORK")
    print("=" * 50)

    scrape_cogwork(source=None)

    print("\n[2/2] Upload events...")
    upload_cogwork(source=None)

    print("\n" + "=" * 50)
    print("COGWORK SYNC COMPLETE")
    print("=" * 50)
    return True
