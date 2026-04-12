import json
import logging
from datetime import date
from pathlib import Path

import click

import config
from src.models.bygdegardarna import fetch_markerdata

logging.basicConfig(level=config.loglevel)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("data") / "bygdegardarna"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    today_str = date.today().strftime("%Y-%m-%d")
    output_file = OUTPUT_DIR / f"{today_str}.json"

    if output_file.exists():
        if not click.confirm(
            f"[{today_str}] {output_file} already exists. Skip scraping?", default=True
        ):
            print(f"Removing {output_file} and continuing...")
            output_file.unlink()
        else:
            print(f"Skipping bygdegardarna - already scraped today.")
            return

    print("Fetching marker data from bygdegardarna.se...")
    venues = fetch_markerdata()
    print(f"Found {len(venues)} venues.")

    output_file.write_text(json.dumps(venues, indent=2, ensure_ascii=False) + "\n")
    print(f"Saved to {output_file}") 


if __name__ == "__main__":
    main()
