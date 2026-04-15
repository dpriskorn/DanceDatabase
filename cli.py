#!/usr/bin/env python3
"""CLI for DanceDB operations."""
import sys
from datetime import date

sys.path.insert(0, str(__file__).rsplit("/", 1)[0])

COMMANDS = {
    "DANSLOGEN": [
        ("scrape-danslogen", "Fetch danslogen event rows"),
        ("scrape-danslogen-artists", "Fetch artists from danslogen"),
        ("ensure-danslogen-venues", "Ensure danslogen venues exist in DanceDB"),
        ("upload-danslogen-events", "Upload danslogen events to DanceDB"),
        ("ensure-danslogen-venues", "Ensure danslogen venues exist in DanceDB"),
        ("ensure-event-venues", "Ensure event venues exist in DanceDB"),
    ],
    "VENUES": [
        ("scrape-bygdegardarna", "Fetch bygdegardarna venues with coordinates"),
        ("scrape-dancedb-venues", "Fetch existing venues from DanceDB"),
        ("match-bygdegardarna-venues", "Match bygdegardarna venues to DanceDB"),
    ],
    "ONBEAT": [
        ("scrape-onbeat", "Fetch events"),
        ("ensure-venues-onbeat", "Ensure venues exist"),
        ("upload-onbeat", "Upload to DanceDB"),
    ],
    "COGWORK": [
        ("scrape-cogwork", "Fetch cogwork events from ALL sources"),
        ("upload-cogwork", "Upload cogwork events to DanceDB"),
    ],
    "FOLKETSHUS": [
        ("scrape-folketshus", "Fetch folketshus och parker venues"),
    ],
    "WIKIDATA": [
        ("scrape-wikidata-artists", "Fetch artists from Wikidata"),
        ("match-wikidata-artists", "Match DanceDB artists to Wikidata"),
        ("sync-wikidata-artists", "Create missing artists from danslogen"),
    ],
    "SYNC (FULL WORKFLOWS)": [
        ("sync-danslogen", "bygdegardarna → folketshus → scrape → match → ensure-venues → upload"),
        ("sync-bygdegardarna", "scrape → fetch-dancedb → match-bygdegardarna-venues"),
        ("sync-onbeat", "scrape + upload"),
        ("sync-cogwork", "scrape + upload"),
        ("sync-folketshus", "scrape + match"),
        ("sync-all", "Sync all sources in sequence"),
        ("scrape-all", "Scrape all data sources at once"),
    ],
}

from src.models.cogwork.scrape import scrape as scrape_cogwork
from src.models.cogwork.upload import upload as upload_cogwork
from src.models.dancedb.run import run as ensure_events
from src.models.dancedb.sync import scrape_all, sync_all, sync_bygdegardarna, sync_cogwork, sync_danslogen, sync_folketshus, sync_onbeat
from src.models.dancedb.venue_ops import ensure_venues, match_venues, scrape_bygdegardarna, scrape_dancedb_venues
from src.models.danslogen.artists.scrape import scrape_artists
from src.models.danslogen.events.scrape import scrape_danslogen, upload_events
from src.models.folketshus.venue import run as scrape_folketshus
from src.models.onbeat.run import run as scrape_onbeat
from src.models.wikidata.operations import match_wikidata_artists, scrape_wikidata_artists, sync_wikidata_artists


def print_commands():
    print("DanceDB CLI Commands\n")
    for category, commands in COMMANDS.items():
        print(f"{category}:")
        for cmd, desc in commands:
            print(f"  {cmd:<30} {desc}")
        print()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="DanceDB CLI")
    parser.add_argument("-l", "--list", action="store_true", help="List available commands")
    parser.add_argument("command", nargs="?", default=None)
    args = parser.parse_args()
    if args.list:
        print_commands()
        return
    if args.command is None:
        print_commands()
        return

    valid_commands = set()
    for commands in COMMANDS.values():
        for cmd, _ in commands:
            valid_commands.add(cmd)

    if args.command not in valid_commands:
        print(f"Unknown command: {args.command}\n")
        print_commands()
        return

    sub = parser.add_subparsers(dest="command")
    p = sub.add_parser("scrape-bygdegardarna", help="Fetch bygdegardarna venues with coordinates")
    p.add_argument("-d", "--date", default=None, help="Date for output (YYYY-MM-DD, default: today)")

    p = sub.add_parser("scrape-danslogen", help="Fetch danslogen event rows")
    p.add_argument("-m", "--month", default="april", help="Month name (default: april)")
    p.add_argument("-y", "--year", type=int, default=2026, help="Year (default: 2026)")

    p = sub.add_parser("scrape-danslogen-artists", help="Fetch artists from danslogen")
    p.add_argument("-d", "--date", default=None, help="Date for output (YYYY-MM-DD, default: today)")

    p = sub.add_parser("scrape-dancedb-venues", help="Fetch existing venues from DanceDB")
    p.add_argument("-d", "--date", default=None, help="Date for output (YYYY-MM-DD, default: today)")

    p = sub.add_parser("match-bygdegardarna-venues", help="Match bygdegardarna venues to DanceDB")
    p.add_argument("-d", "--date", default=None, help="Date for input files (YYYY-MM-DD, default: today)")
    p.add_argument("--skip-prompts", action="store_true", help="Skip interactive prompts, auto-match fuzzy >=85")

    p = sub.add_parser("ensure-danslogen-venues", help="Ensure danslogen venues exist in DanceDB")
    p.add_argument("-d", "--date", default=None, help="Date for venue data (YYYY-MM-DD, default: today)")
    p.add_argument("--dry-run", action="store_true", help="Preview without uploading")

    p = sub.add_parser("ensure-event-venues", help="Ensure event venues exist in DanceDB")
    p.add_argument("-m", "--month", default="april", help="Month name (default: april)")
    p.add_argument("-y", "--year", type=int, default=2026, help="Year (default: 2026)")
    p.add_argument("--dry-run", action="store_true", help="Preview only, don't abort")

    p = sub.add_parser("upload-danslogen-events", help="Upload danslogen events to DanceDB")
    p.add_argument("-i", "--input-file", default="data/danslogen/april.json", help="Input JSON file")
    p.add_argument("-d", "--date", default=None, help="Date for venue data (YYYY-MM-DD, default: today)")
    p.add_argument("-m", "--month", default="april", help="Month name (default: april)")
    p.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    p.add_argument("-l", "--limit", type=int, default=None, help="Limit number of rows to process")
    p.add_argument("--yes", action="store_true", help="Skip confirmation prompts")

    # === ONBEAT ===
    p = sub.add_parser("scrape-onbeat", help="Fetch events")
    p = sub.add_parser("ensure-venues-onbeat", help="Ensure venues exist")
    p.add_argument("--date", default=None, help="Date of scraped data (default: today)")
    p.add_argument("--dry-run", action="store_true", help="Preview without creating")
    p = sub.add_parser("upload-onbeat", help="Upload to DanceDB")
    p.add_argument("--dry-run", action="store_true", help="Preview without uploading")

    # === COGWORK ===
    p = sub.add_parser("scrape-cogwork", help="Fetch cogwork events from ALL sources")
    p.add_argument("-s", "--source", default=None, help="Specific source (default: all)")
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing output files")

    p = sub.add_parser("upload-cogwork", help="Upload cogwork events to DanceDB")
    p.add_argument("-s", "--source", default=None, help="Specific source (default: all)")
    p.add_argument("--dry-run", action="store_true", help="Preview without uploading")

    # === FOLKETSHUS ===
    p = sub.add_parser("scrape-folketshus", help="Fetch folketshus och parker venues")
    p.add_argument("-d", "--date", default=None, help="Date for output (YYYY-MM-DD, default: today)")
    p.add_argument("-m", "--match", action="store_true", help="Match venues to DanceDB and create new venues")

    # === WIKIDATA ===
    p = sub.add_parser("scrape-wikidata-artists", help="Fetch artists from Wikidata")
    p.add_argument("-d", "--date", default=None, help="Date for output (YYYY-MM-DD, default: today)")

    p = sub.add_parser("match-wikidata-artists", help="Match DanceDB artists to Wikidata and upload P3")
    p.add_argument("-d", "--date", default=None, help="Date for Wikidata artists file (YYYY-MM-DD, default: today)")
    p.add_argument("--dry-run", action="store_true", help="Preview without uploading")

    p = sub.add_parser("sync-wikidata-artists", help="Create missing artists from danslogen in DanceDB with Wikidata match")
    p.add_argument("-d", "--date", default=None, help="Date for Wikidata artists file (YYYY-MM-DD, default: today)")
    p.add_argument("-m", "--month", default="april", help="Month name for danslogen (default: april)")
    p.add_argument("-y", "--year", type=int, default=2026, help="Year for danslogen (default: 2026)")
    p.add_argument("--dry-run", action="store_true", help="Preview without uploading")

    # === SCRAPE COMMANDS ===
    p = sub.add_parser("scrape-all", help="Scrape all data sources at once")
    p.add_argument("-m", "--month", default=None, help="Month name (default: current month)")
    p.add_argument("-y", "--year", type=int, default=None, help="Year (default: current year)")

    # === SYNC COMMANDS ===
    p = sub.add_parser("sync-danslogen", help="Sync danslogen: sync-wikidata → scrape → ensure-danslogen-venues → upload-danslogen-events")
    p.add_argument("-m", "--month", default=None, help="Month name (default: current month)")
    p.add_argument("-y", "--year", type=int, default=None, help="Year (default: current year)")
    p.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    p.add_argument("-l", "--limit", type=int, default=None, help="Limit number of events")
    p.add_argument("-f", "--force", action="store_true", help="Force run even if prerequisites met")
    p.add_argument("--only-scrape", action="store_true", help="Only scrape, skip uploads")

    p = sub.add_parser("sync-bygdegardarna", help="Sync bygdegardarna: scrape → fetch-dancedb → match-bygdegardarna-venues")
    p.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    p.add_argument("-f", "--force", action="store_true", help="Force run even if prerequisites met")
    p.add_argument("--only-scrape", action="store_true", help="Only scrape, skip uploads")

    p = sub.add_parser("sync-onbeat", help="Sync onbeat: scrape + upload")
    p.add_argument("--dry-run", action="store_true", help="Preview without uploading")

    p = sub.add_parser("sync-cogwork", help="Sync cogwork: scrape + upload")
    p.add_argument("--dry-run", action="store_true", help="Preview without uploading")

    p = sub.add_parser("sync-folketshus", help="Sync folketshus: scrape + match")
    p.add_argument("--dry-run", action="store_true", help="Preview without uploading")

    p = sub.add_parser("sync-all", help="Sync all sources in sequence")
    p.add_argument("-m", "--month", default=None, help="Month name (default: current month)")
    p.add_argument("-y", "--year", type=int, default=None, help="Year (default: current year)")
    p.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    p.add_argument("-l", "--limit", type=int, default=None, help="Limit number of events")
    p.add_argument("-f", "--force", action="store_true", help="Force run even if prerequisites met")
    p.add_argument("--only-scrape", action="store_true", help="Only scrape, skip uploads")

    args = parser.parse_args()

    # SCRAPE ALL
    if args.command == "scrape-all":
        month = args.month
        year = args.year
        if month is None or year is None:
            from src.models.dancedb.sync import get_current_month_year

            month, year = get_current_month_year()
        scrape_all(month=month, year=year)

    # DANSLOGEN
    if args.command == "scrape-bygdegardarna":
        date_str = getattr(args, "date", None) or date.today().strftime("%Y-%m-%d")
        scrape_bygdegardarna(date_str)

    elif args.command == "scrape-danslogen":
        scrape_danslogen(args.month, args.year)

    elif args.command == "scrape-danslogen-artists":
        date_str = getattr(args, "date", None) or date.today().strftime("%Y-%m-%d")
        scrape_artists(date_str)

    elif args.command == "scrape-dancedb-venues":
        date_str = getattr(args, "date", None) or date.today().strftime("%Y-%m-%d")
        scrape_dancedb_venues(date_str)

    elif args.command == "match-bygdegardarna-venues":
        date_str = getattr(args, "date", None) or date.today().strftime("%Y-%m-%d")
        match_venues(date_str, skip_prompts=args.skip_prompts)

    elif args.command == "ensure-danslogen-venues":
        date_str = getattr(args, "date", None) or date.today().strftime("%Y-%m-%d")
        ensure_venues(date_str, dry_run=args.dry_run)

    elif args.command == "ensure-event-venues":
        ensure_events(month=args.month, year=args.year, dry_run=args.dry_run)

    elif args.command == "upload-events":
        date_str = getattr(args, "date", None) or date.today().strftime("%Y-%m-%d")
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
        print("upload-onbeat is not yet implemented. Use sync-onbeat instead.")
        # upload_onbeat(dry_run=args.dry_run)

    elif args.command == "onbeat-ensure-venues":
        from src.models.dancedb.venue_ops import onbeat_ensure_venues

        date_str = getattr(args, "date", None) or date.today().strftime("%Y-%m-%d")
        onbeat_ensure_venues(date_str, dry_run=args.dry_run)

    # COGWORK
    elif args.command == "scrape-cogwork":
        scrape_cogwork(source=args.source, overwrite=args.overwrite)

    elif args.command == "upload-cogwork":
        upload_cogwork(source=args.source, dry_run=args.dry_run)

    # FOLKETSHUS
    elif args.command == "scrape-folketshus":
        scrape_folketshus(date_str=getattr(args, "date", None), match=args.match)

    # SYNC COMMANDS
    elif args.command == "sync-danslogen":
        sync_danslogen(
            month=args.month,
            year=args.year,
            dry_run=args.dry_run,
            limit=args.limit,
            force=args.force,
            only_scrape=args.only_scrape,
        )

    elif args.command == "sync-bygdegardarna":
        sync_bygdegardarna(dry_run=args.dry_run, force=args.force, only_scrape=args.only_scrape)

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
            force=args.force,
            only_scrape=args.only_scrape,
        )

    # WIKIDATA
    elif args.command == "scrape-wikidata-artists":
        date_str = getattr(args, "date", None) or date.today().strftime("%Y-%m-%d")
        scrape_wikidata_artists(date_str)

    elif args.command == "match-wikidata-artists":
        date_str = getattr(args, "date", None) or date.today().strftime("%Y-%m-%d")
        match_wikidata_artists(date_str, dry_run=args.dry_run)

    elif args.command == "sync-wikidata-artists":
        date_str = getattr(args, "date", None) or date.today().strftime("%Y-%m-%d")
        sync_wikidata_artists(date_str, month=args.month, year=args.year, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
