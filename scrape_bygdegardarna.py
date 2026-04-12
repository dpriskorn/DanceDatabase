import json
import logging
from datetime import date
from pathlib import Path

import config
from src.models.bygdegardarna import fetch_markerdata

logging.basicConfig(level=config.loglevel)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("data") / "bygdegardarna"


def main():
    parser = argparse.ArgumentParser(description="Scrape bygdegardarna venues")
    parser.add_argument("--date", default=None, help="Date string for output file (YYYY-MM-DD, default: today)")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    today_str = args.date or date.today().strftime("%Y-%m-%d")
    output_file = OUTPUT_DIR / f"{today_str}.json"

    if output_file.exists():
        print(f"Overwriting existing file {output_file}")
        output_file.unlink()

    print("Fetching marker data from bygdegardarna.se...")
    venues = fetch_markerdata()
    print(f"Found {len(venues)} venues.")

    output_file.write_text(json.dumps(venues, indent=2, ensure_ascii=False) + "\n")
    print(f"Saved to {output_file}")


if __name__ == "__main__":
    main()
