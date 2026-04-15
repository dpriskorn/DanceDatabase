from src.models.cogwork.scrape import get_scrapers


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
