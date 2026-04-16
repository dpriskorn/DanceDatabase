"""Sync for bygdegardarna data source."""
from datetime import date
from pathlib import Path

from src.models.pipeline import Pipeline
from src.models.dancedb.venue_ops import match_venues, scrape_bygdegardarna, scrape_dancedb_venues


def get_data_dir() -> Path:
    """Get the data directory path."""
    import config

    return config.data_dir


def sync_bygdegardarna(
    only_scrape: bool = False,
) -> bool:
    """Sync bygdegardarna venues with prerequisite checking."""
    date_str = date.today().strftime("%Y-%m-%d")
    data_dir = get_data_dir()

    bygdegardarna_file = data_dir / "bygdegardarna" / f"{date_str}.json"
    dancedb_venues_file = data_dir / "dancedb" / "venues" / f"{date_str}.json"
    enriched_file = data_dir / "bygdegardarna" / "enriched" / f"{date_str}.json"

    print("\n" + "=" * 50)
    print("SYNC BYGDEGARDARNA")
    print("=" * 50)

    pipeline = Pipeline(name="bygdegardarna")
    pipeline.add_step(
        "1. Scrape bygdegardarna venues",
        lambda: scrape_bygdegardarna(date_str=date_str),
        output_files=[bygdegardarna_file],
    )
    pipeline.add_step(
        "2. Fetch existing DanceDB venues",
        lambda: scrape_dancedb_venues(date_str=date_str),
        output_files=[dancedb_venues_file],
    )
    pipeline.add_step(
        "3. Match venues to DanceDB",
        lambda: match_venues(date_str=date_str, skip_prompts=True),
        input_files=[bygdegardarna_file, dancedb_venues_file],
        output_files=[enriched_file],
    )

    pipeline.run(only_scrape=only_scrape)

    print("\n" + "=" * 50)
    print("BYGDEGARDARNA SYNC COMPLETE")
    print("=" * 50)
    return True
