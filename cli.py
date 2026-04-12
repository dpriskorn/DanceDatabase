#!/usr/bin/env python3
"""CLI for DanceDB operations."""
import argparse
import sys
from datetime import date

sys.path.insert(0, str(__file__).rsplit('/', 1)[0])

from src.models.dancedb.venue_ops import (
    scrape_bygdegardarna,
    scrape_dancedb_venues,
    match_venues,
    ensure_venues,
)
from src.models.dancedb.event_ops import (
    scrape_danslogen,
    upload_events,
)
from src.models.dancedb.onbeat_ops import (
    scrape_onbeat,
    upload_onbeat,
)
from src.models.dancedb.cogwork_ops import (
    scrape_cogwork,
    upload_cogwork,
)
from src.models.commands.folketshus import run as scrape_folketshus
from src.models.dancedb.workflow import run_all


def main():
    parser = argparse.ArgumentParser(description="DanceDB CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # === DANSLOGEN ===
    p = sub.add_parser("scrape-bygdegardarna",
                     help="Fetch bygdegardarna venues with coordinates")
    p.add_argument("-d", "--date", default=None,
                   help="Date for output (YYYY-MM-DD, default: today)")

    p = sub.add_parser("scrape-danslogen",
                     help="Fetch danslogen event rows")
    p.add_argument("-m", "--month", default="april",
                   help="Month name (default: april)")
    p.add_argument("-y", "--year", type=int, default=2026,
                   help="Year (default: 2026)")

    p = sub.add_parser("scrape-dancedb-venues",
                     help="Fetch existing venues from DanceDB")
    p.add_argument("-d", "--date", default=None,
                   help="Date for output (YYYY-MM-DD, default: today)")

    p = sub.add_parser("match-venues",
                     help="Match bygdegardarna venues to DanceDB")
    p.add_argument("-d", "--date", default=None,
                   help="Date for input files (YYYY-MM-DD, default: today)")
    p.add_argument("--skip-prompts", action="store_true",
                   help="Skip interactive prompts, auto-match fuzzy >=85")

    p = sub.add_parser("ensure-venues",
                     help="Ensure danslogen venues exist in DanceDB")
    p.add_argument("-d", "--date", default=None,
                   help="Date for venue data (YYYY-MM-DD, default: today)")
    p.add_argument("--dry-run", action="store_true",
                   help="Preview without uploading")

    p = sub.add_parser("upload-events",
                     help="Upload danslogen events to DanceDB")
    p.add_argument("-i", "--input-file",
                   default="data/danslogen_rows_2026_april.json",
                   help="Input JSON file")
    p.add_argument("-d", "--date", default=None,
                   help="Date for venue data (YYYY-MM-DD, default: today)")
    p.add_argument("-m", "--month", default="april",
                   help="Month name (default: april)")
    p.add_argument("--dry-run", action="store_true",
                   help="Preview without uploading")
    p.add_argument("-l", "--limit", type=int, default=None,
                   help="Limit number of rows to process")
    p.add_argument("--yes", action="store_true",
                   help="Skip confirmation prompts")

    # === ONBEAT ===
    p = sub.add_parser("scrape-onbeat",
                     help="Fetch onbeat events")

    p = sub.add_parser("upload-onbeat",
                     help="Upload onbeat events to DanceDB")
    p.add_argument("--dry-run", action="store_true",
                   help="Preview without uploading")

# === COGWORK ===
    p = sub.add_parser("scrape-cogwork",
                      help="Fetch cogwork events from ALL sources")
    p.add_argument("-s", "--source", default=None,
                   help="Specific source (default: all)")

    p = sub.add_parser("upload-cogwork",
                      help="Upload cogwork events to DanceDB")
    p.add_argument("-s", "--source", default=None,
                   help="Specific source (default: all)")
    p.add_argument("--dry-run", action="store_true",
                   help="Preview without uploading")

    # === FOLKETSHUS ===
    p = sub.add_parser("scrape-folketshus",
                       help="Fetch folketshus och parker venues")
    p.add_argument("-d", "--date", default=None,
                  help="Date for output (YYYY-MM-DD, default: today)")

    # === WORKFLOW ===
    p = sub.add_parser("run-all",
                       help="Full workflow: scrape → match → upload")
    p.add_argument("-m", "--month", default="april",
                    help="Month name (default: april)")
    p.add_argument("-y", "--year", type=int, default=2026,
                    help="Year (default: 2026)")
    p.add_argument("--dry-run", action="store_true",
                    help="Preview without uploading")
    p.add_argument("-l", "--limit", type=int, default=None,
                    help="Limit number of rows")

    args = parser.parse_args()

    # DANSLOGEN
    if args.command == "scrape-bygdegardarna":
        date_str = getattr(args, 'date', None) or date.today().strftime("%Y-%m-%d")
        scrape_bygdegardarna(date_str)

    elif args.command == "scrape-danslogen":
        scrape_danslogen(args.month, args.year)

    elif args.command == "scrape-dancedb-venues":
        date_str = getattr(args, 'date', None) or date.today().strftime("%Y-%m-%d")
        scrape_dancedb_venues(date_str)

    elif args.command == "match-venues":
        date_str = getattr(args, 'date', None) or date.today().strftime("%Y-%m-%d")
        match_venues(date_str, skip_prompts=args.skip_prompts)

    elif args.command == "ensure-venues":
        date_str = getattr(args, 'date', None) or date.today().strftime("%Y-%m-%d")
        ensure_venues(date_str, dry_run=args.dry_run)

    elif args.command == "upload-events":
        date_str = getattr(args, 'date', None) or date.today().strftime("%Y-%m-%d")
        upload_events(
            input_file=args.input_file,
            date_str=date_str,
            month=args.month,
            dry_run=args.dry_run,
            limit=args.limit,
            yes=args.yes,
        )

    # ONBEAT
    elif args.command == "scrape-onbeat":
        scrape_onbeat()

    elif args.command == "upload-onbeat":
        upload_onbeat(dry_run=args.dry_run)

    # COGWORK
    elif args.command == "scrape-cogwork":
        scrape_cogwork(source=args.source)

    elif args.command == "upload-cogwork":
        upload_cogwork(source=args.source, dry_run=args.dry_run)

    # FOLKETSHUS
    elif args.command == "scrape-folketshus":
        scrape_folketshus(date_str=getattr(args, 'date', None))

    # WORKFLOW
    elif args.command == "run-all":
        run_all(
            month=args.month,
            year=args.year,
            dry_run=args.dry_run,
            limit=args.limit,
        )


if __name__ == "__main__":
    main()