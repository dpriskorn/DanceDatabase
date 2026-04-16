"""Onbeat CLI commands."""
from datetime import date as dt

from src.cli.base import get_date_str


def add_onbeat_subparsers(sub) -> dict:
    """Add onbeat subparsers and return command handlers."""
    handlers = {}
    
    p = sub.add_parser("scrape-onbeat", help="Fetch events")
    handlers["scrape-onbeat"] = _scrape_onbeat
    
    p = sub.add_parser("ensure-venues-onbeat", help="Ensure venues exist")
    p.add_argument("--date", default=None, help="Date of scraped data (default: today)")
    handlers["ensure-venues-onbeat"] = _ensure_venues_onbeat
    
    p = sub.add_parser("upload-onbeat", help="Upload to DanceDB")
    handlers["upload-onbeat"] = _upload_onbeat
    
    p = sub.add_parser("onbeat-ensure-venues", help="Ensure venues exist")
    p.add_argument("--date", default=None, help="Date of scraped data (default: today)")
    handlers["onbeat-ensure-venues"] = _onbeat_ensure_venues
    
    return handlers


def _scrape_onbeat(args) -> None:
    from src.models.onbeat.run import run as scrape_onbeat
    scrape_onbeat()


def _ensure_venues_onbeat(args) -> None:
    from src.models.dancedb.venue_ops import onbeat_ensure_venues
    date_str = get_date_str(args.date)
    onbeat_ensure_venues(date_str)


def _upload_onbeat(args) -> None:
    print("upload-onbeat is not yet implemented. Use sync-onbeat instead.")


def _onbeat_ensure_venues(args) -> None:
    from src.models.dancedb.venue_ops import onbeat_ensure_venues
    date_str = get_date_str(args.date)
    onbeat_ensure_venues(date_str)
