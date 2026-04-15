#!/usr/bin/env python3
"""Upload Danslogen scraped data to DanceDB.

Reads from data/danslogen_rows_YYYY_MM.json, processes bands and venues,
and uploads events to DanceDB via DancedbClient.
"""
import argparse
import sys

sys.path.insert(0, str(__file__).rsplit("/", 1)[0])

from src.models.danslogen.uploader import DanslogenUploader


def main():
    """Upload Danslogen scraped data to DanceDB."""
    parser = argparse.ArgumentParser(description="Upload Danslogen scraped data to DanceDB")
    parser.add_argument("-i", "--input-file", default="data/danslogen_rows_2026_april.json", help="Input JSON file with scraped rows")
    parser.add_argument("-m", "--month", default="april", help="Month name for URL construction")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Process but do not upload to DanceDB")
    parser.add_argument("-l", "--limit", type=int, default=None, help="Limit number of rows to process")
    parser.add_argument("-d", "--date", default=None, help="Date for venue matching (YYYY-MM-DD, default: today)")
    args = parser.parse_args()

    uploader = DanslogenUploader(
        filename=args.input_file,
        date_str=args.date,
        month=args.month,
        limit=args.limit,
    )

    processed, events, skipped = uploader.run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
