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
from src.models.commands.onbeat import run as scrape_onbeat
from src.models.commands.cogwork import scrape as scrape_cogwork, upload as upload_cogwork
from src.models.commands.folketshus import run as scrape_folketshus
from src.models.commands.ensure_events import run as ensure_events
from src.models.commands.sync import (
    sync_danslogen,
    sync_bygdegardarna,
    sync_onbeat,
    sync_cogwork,
    sync_folketshus,
    sync_all,
)
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

    p = sub.add_parser("ensure-events",
                      help="Ensure all event venues exist in DanceDB (aborts if missing)")
    p.add_argument("-m", "--month", default="april",
                  help="Month name (default: april)")
    p.add_argument("-y", "--year", type=int, default=2026,
                  help="Year (default: 2026)")
    p.add_argument("--dry-run", action="store_true",
                  help="Preview only, don't abort")

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
    p.add_argument("-m", "--match", action="store_true",
                  help="Match venues to DanceDB and create new venues")

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

    # === SYNC COMMANDS ===
    p = sub.add_parser("sync-danslogen",
                       help="Sync danslogen: scrape → ensure-venues → upload → ensure-events")
    p.add_argument("-m", "--month", default=None,
                    help="Month name (default: current month)")
    p.add_argument("-y", "--year", type=int, default=None,
                    help="Year (default: current year)")
    p.add_argument("--dry-run", action="store_true",
                    help="Preview without uploading")
    p.add_argument("-l", "--limit", type=int, default=None,
                    help="Limit number of events")

    p = sub.add_parser("sync-bygdegardarna",
                       help="Sync bygdegardarna: scrape → fetch-dancedb → match-venues")
    p.add_argument("--dry-run", action="store_true",
                    help="Preview without uploading")

    p = sub.add_parser("sync-onbeat",
                       help="Sync onbeat: scrape + upload")
    p.add_argument("--dry-run", action="store_true",
                    help="Preview without uploading")

    p = sub.add_parser("sync-cogwork",
                       help="Sync cogwork: scrape + upload")
    p.add_argument("--dry-run", action="store_true",
                    help="Preview without uploading")

    p = sub.add_parser("sync-folketshus",
                       help="Sync folketshus: scrape + match")
    p.add_argument("--dry-run", action="store_true",
                    help="Preview without uploading")

    p = sub.add_parser("sync-all",
                       help="Sync all sources in sequence")
    p.add_argument("-m", "--month", default=None,
                    help="Month name (default: current month)")
    p.add_argument("-y", "--year", type=int, default=None,
                    help="Year (default: current year)")
    p.add_argument("--dry-run", action="store_true",
                    help="Preview without uploading")
    p.add_argument("-l", "--limit", type=int, default=None,
                    help="Limit number of events")

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

    elif args.command == "ensure-events":
        ensure_events(month=args.month, year=args.year, dry_run=args.dry_run)

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
        scrape_folketshus(date_str=getattr(args, 'date', None), match=args.match)

    # WORKFLOW
    elif args.command == "run-all":
        run_all(
            month=args.month,
            year=args.year,
            dry_run=args.dry_run,
            limit=args.limit,
        )

    # SYNC COMMANDS
    elif args.command == "sync-danslogen":
        sync_danslogen(
            month=args.month,
            year=args.year,
            dry_run=args.dry_run,
            limit=args.limit,
        )

    elif args.command == "sync-bygdegardarna":
        sync_bygdegardarna(dry_run=args.dry_run)

    elif args.command == "sync-onbeat":
        sync_onbeat(dry_run=args.dry_run)

    elif args.command == "sync-cogwork":
        sync_cogwork(dry_run=args.dry_run)

    elif args.command == "sync-folketshus":
        sync_folketshus(dry_run=args.dry_run)

    elif args.command == "sync-all":
        sync_all(
            month=args.month,
            year=args.year,
            dry_run=args.dry_run,
            limit=args.limit,
        )


if __name__ == "__main__":
    main()