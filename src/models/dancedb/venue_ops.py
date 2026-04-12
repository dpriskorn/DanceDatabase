"""Venue operations: scrape, match, ensure exist."""
import logging
import json
import subprocess
from pathlib import Path
from datetime import date

from src.models.dancedb.config import config

logger = logging.getLogger(__name__)


def scrape_bygdegardarna(date_str: str | None = None) -> None:
    """Fetch venues from bygdegardarna.se with coordinates."""
    date_str = date_str or date.today().strftime("%Y-%m-%d")
    print(f"\n=== Step 1: Scrape bygdegardarna venues ===")

    result = subprocess.run(
        ["poetry", "run", "python", "scrape_bygdegardarna.py"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError("scrape_bygdegardarna.py failed")
    print(result.stdout)
    print(f"Saved to data/bygdegardarna/{date_str}.json")


def scrape_dancedb_venues(date_str: str | None = None) -> None:
    """Fetch existing venues from DanceDB."""
    date_str = date_str or date.today().strftime("%Y-%m-%d")
    print(f"\n=== Step 2: Scrape DanceDB venues ===")

    result = subprocess.run(
        ["poetry", "run", "python", "scrape_venues_from_dancedb.py"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError("scrape_venues_from_dancedb.py failed")
    print(result.stdout)
    print(f"Saved to data/dancedb/venues/{date_str}.json")


def match_venues(date_str: str | None = None, skip_prompts: bool = False) -> None:
    """Match bygdegardarna venues to DanceDB."""
    date_str = date_str or date.today().strftime("%Y-%m-%d")
    print(f"\n=== Step 3: Match venues ===")

    cmd = ["poetry", "run", "python", "scrape_bygdegardarna_match.py", f"--date={date_str}"]
    if skip_prompts:
        cmd.append("--skip-prompts")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError("scrape_bygdegardarna_match.py failed")
    print(result.stdout)


def ensure_venues(date_str: str | None = None, dry_run: bool = False) -> None:
    """Ensure danslogen venues exist in DanceDB before uploading events."""
    date_str = date_str or date.today().strftime("%Y-%m-%d")
    print(f"\n=== Ensuring venues exist for {date_str} ===")

    byg_path = config.bygdegardarna_dir / f"{date_str}.json"
    db_path = config.dancedb_dir / "venues" / f"{date_str}.json"

    if not byg_path.exists():
        print(f"Error: bygdegardarna data not found: {byg_path}")
        print("Run: cli.py scrape-bygdegardarna first")
        return

    if not db_path.exists():
        print(f"Error: DanceDB venues not found: {db_path}")
        print("Run: cli.py scrape-dancedb-venues first")
        return

    print(f"Loaded {byg_path}")
    print(f"Loaded {db_path}")

    if dry_run:
        print("DRY RUN - no venues will be created")

    print("\nVenue matching done. Run 'cli.py upload-events' to process events.")