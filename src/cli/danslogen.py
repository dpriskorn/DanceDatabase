"""Danslogen CLI commands."""
from datetime import date as dt

from src.cli.base import get_date_str


def add_danslogen_subparsers(sub) -> dict:
    """Add danslogen subparsers and return command handlers."""
    handlers = {}
    
    p = sub.add_parser("scrape-danslogen", help="Fetch danslogen event rows")
    p.add_argument("-m", "--month", default="april", help="Month name (default: april)")
    p.add_argument("-y", "--year", type=int, default=2026, help="Year (default: 2026)")
    handlers["scrape-danslogen"] = _scrape_danslogen
    
    p = sub.add_parser("scrape-danslogen-artists", help="Fetch artists from danslogen")
    p.add_argument("-d", "--date", default=None, help="Date for output (YYYY-MM-DD, default: today)")
    handlers["scrape-danslogen-artists"] = _scrape_danslogen_artists
    
    p = sub.add_parser("ensure-danslogen-venues", help="Ensure danslogen venues exist in DanceDB")
    p.add_argument("-d", "--date", default=None, help="Date for venue data (YYYY-MM-DD, default: today)")
    handlers["ensure-danslogen-venues"] = _ensure_danslogen_venues
    
    p = sub.add_parser("ensure-event-venues", help="Ensure event venues exist in DanceDB")
    p.add_argument("-m", "--month", default="april", help="Month name (default: april)")
    p.add_argument("-y", "--year", type=int, default=2026, help="Year (default: 2026)")
    handlers["ensure-event-venues"] = _ensure_event_venues
    
    p = sub.add_parser("upload-danslogen-events", help="Upload danslogen events to DanceDB")
    p.add_argument("-i", "--input-file", default="data/danslogen/april.json", help="Input JSON file")
    p.add_argument("-d", "--date", default=None, help="Date for venue data (YYYY-MM-DD, default: today)")
    p.add_argument("-m", "--month", default="april", help="Month name (default: april)")
    p.add_argument("-l", "--limit", type=int, default=None, help="Limit number of rows to process")
    handlers["upload-danslogen-events"] = _upload_danslogen_events
    
    return handlers


def _scrape_danslogen(args) -> None:
    from src.models.danslogen.events.scrape import scrape_danslogen
    scrape_danslogen(args.month, args.year)


def _scrape_danslogen_artists(args) -> None:
    from src.models.danslogen.artists.scrape import scrape_artists
    date_str = get_date_str(args.date)
    scrape_artists(date_str)


def _ensure_danslogen_venues(args) -> None:
    from src.models.dancedb.venue_ops import ensure_venues
    date_str = get_date_str(args.date)
    ensure_venues(date_str)


def _ensure_event_venues(args) -> None:
    from src.models.dancedb.run import run as ensure_events
    ensure_events(month=args.month, year=args.year)


def _upload_danslogen_events(args) -> None:
    from src.models.danslogen.events.scrape import upload_events
    date_str = get_date_str(args.date)
    upload_events(
        input_file=args.input_file,
        date_str=date_str,
        month=args.month,
        limit=args.limit,
    )
