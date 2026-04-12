"""Event operations: scrape danslogen, upload events."""
import logging
import subprocess
from pathlib import Path

from src.models.dancedb.config import config
from src.models.danslogen.uploader import DanslogenUploader

logger = logging.getLogger(__name__)


def scrape_danslogen(month: str = "april", year: int = 2026) -> None:
    """Fetch event rows from danslogen.se."""
    print(f"\n=== Scrape danslogen events for {month} {year} ===")

    result = subprocess.run(
        ["python", "scrape_danslogen.py", f"--month={month}"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError("scrape_danslogen.py failed")
    print(result.stdout)
    print(f"Saved to data/danslogen_rows_{year}_{month}.json")


def upload_events(
    input_file: str = "data/danslogen_rows_2026_april.json",
    date_str: str | None = None,
    month: str = "april",
    dry_run: bool = False,
    limit: int | None = None,
) -> None:
    """Upload danslogen events to DanceDB."""
    print(f"\n=== Upload danslogen events ===")

    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_file}")
        return

    uploader = DanslogenUploader(
        filename=input_file,
        date_str=date_str,
        month=month,
        limit=limit,
    )

    processed, events, skipped = uploader.run(dry_run=dry_run)

    if dry_run:
        print("\nDry run complete. Run without --dry-run to upload.")
    else:
        print(f"\nDone! Uploaded {events} events, {skipped} skipped.")