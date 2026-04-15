"""Artist operations: scrape artists from danslogen.se."""
import json
import logging
from pathlib import Path

import config
from src.models.danslogen.main import Danslogen

logger = logging.getLogger(__name__)


def scrape_artists(date_str: str) -> None:
    """Fetch artists from danslogen.se/dansband/alla.
    
    Args:
        date_str: Date string for output filename (YYYY-MM-DD)
    """
    artists_dir = Path("data/danslogen/artists")
    output_file = artists_dir / f"{date_str}.json"

    artists_dir.mkdir(parents=True, exist_ok=True)

    d = Danslogen(interactive=False)
    artists = d.scrape_artists()

    print(f"Found {len(artists)} artists")

    with open(output_file, "w") as f:
        json.dump([a.model_dump() for a in artists], f, ensure_ascii=False, indent=2)

    print(f"Saved to {output_file}")