"""Sync workflow CLI commands."""
from src.cli.base import get_date_str, get_month_year


def add_sync_subparsers(sub) -> dict:
    """Add sync subparsers and return command handlers."""
    handlers = {}
    
    p = sub.add_parser("scrape-all", help="Scrape all data sources at once")
    p.add_argument("-m", "--month", default=None, help="Month name (default: current month)")
    p.add_argument("-y", "--year", type=int, default=None, help="Year (default: current year)")
    handlers["scrape-all"] = _scrape_all
    
    p = sub.add_parser("sync-danslogen", help="Sync danslogen: scrape → ensure-venues → upload")
    p.add_argument("-m", "--month", default=None, help="Month name (default: current month)")
    p.add_argument("-y", "--year", type=int, default=None, help="Year (default: current year)")
    p.add_argument("-l", "--limit", type=int, default=None, help="Limit number of events")
    p.add_argument("--only-scrape", action="store_true", help="Only scrape, skip uploads")
    handlers["sync-danslogen"] = _sync_danslogen
    
    p = sub.add_parser("sync-bygdegardarna", help="Sync bygdegardarna: scrape → fetch-dancedb → match")
    p.add_argument("--only-scrape", action="store_true", help="Only scrape, skip uploads")
    handlers["sync-bygdegardarna"] = _sync_bygdegardarna
    
    p = sub.add_parser("sync-onbeat", help="Sync onbeat: scrape + upload")
    handlers["sync-onbeat"] = _sync_onbeat
    
    p = sub.add_parser("sync-cogwork", help="Sync cogwork: scrape + upload")
    handlers["sync-cogwork"] = _sync_cogwork
    
    p = sub.add_parser("sync-folketshus", help="Sync folketshus: scrape + match")
    handlers["sync-folketshus"] = _sync_folketshus
    
    p = sub.add_parser("sync-all", help="Sync all sources in sequence")
    p.add_argument("-m", "--month", default=None, help="Month name (default: current month)")
    p.add_argument("-y", "--year", type=int, default=None, help="Year (default: current year)")
    p.add_argument("-l", "--limit", type=int, default=None, help="Limit number of events")
    p.add_argument("--only-scrape", action="store_true", help="Only scrape, skip uploads")
    handlers["sync-all"] = _sync_all
    
    p = sub.add_parser("scrape-bygdegardarna", help="Fetch bygdegardarna venues with coordinates")
    p.add_argument("-d", "--date", default=None, help="Date for output (YYYY-MM-DD, default: today)")
    handlers["scrape-bygdegardarna"] = _scrape_bygdegardarna
    
    p = sub.add_parser("scrape-dancedb-venues", help="Fetch existing venues from DanceDB")
    p.add_argument("-d", "--date", default=None, help="Date for output (YYYY-MM-DD, default: today)")
    handlers["scrape-dancedb-venues"] = _scrape_dancedb_venues
    
    p = sub.add_parser("match-bygdegardarna-venues", help="Match bygdegardarna venues to DanceDB")
    p.add_argument("-d", "--date", default=None, help="Date for input files (YYYY-MM-DD, default: today)")
    p.add_argument("--skip-prompts", action="store_true", help="Skip interactive prompts, auto-match fuzzy >=85")
    handlers["match-bygdegardarna-venues"] = _match_bygdegardarna_venues
    
    p = sub.add_parser("scrape-folketshus", help="Fetch folketshus och parker venues")
    p.add_argument("-d", "--date", default=None, help="Date for output (YYYY-MM-DD, default: today)")
    handlers["scrape-folketshus"] = _scrape_folketshus
    
    p = sub.add_parser("scrape-wikidata-artists", help="Fetch artists from Wikidata")
    p.add_argument("-d", "--date", default=None, help="Date for output (YYYY-MM-DD, default: today)")
    handlers["scrape-wikidata-artists"] = _scrape_wikidata_artists
    
    p = sub.add_parser("match-wikidata-artists", help="Match DanceDB artists to Wikidata")
    p.add_argument("-d", "--date", default=None, help="Date for Wikidata artists file (YYYY-MM-DD, default: today)")
    handlers["match-wikidata-artists"] = _match_wikidata_artists
    
    p = sub.add_parser("sync-wikidata-artists", help="Create missing artists from danslogen")
    p.add_argument("-d", "--date", default=None, help="Date for Wikidata artists file (YYYY-MM-DD, default: today)")
    p.add_argument("-m", "--month", default="april", help="Month name for danslogen (default: april)")
    p.add_argument("-y", "--year", type=int, default=2026, help="Year for danslogen (default: 2026)")
    handlers["sync-wikidata-artists"] = _sync_wikidata_artists
    
    return handlers


def _scrape_all(args) -> None:
    from src.models.dancedb.sync import scrape_all
    month, year = get_month_year(args.month, args.year)
    scrape_all(month=month, year=year)


def _sync_danslogen(args) -> None:
    from src.models.dancedb.sync import sync_danslogen
    month, year = get_month_year(args.month, args.year)
    sync_danslogen(
        month=month,
        year=year,
        limit=args.limit,
        only_scrape=args.only_scrape,
    )


def _sync_bygdegardarna(args) -> None:
    from src.models.dancedb.sync import sync_bygdegardarna
    sync_bygdegardarna(only_scrape=args.only_scrape)


def _sync_onbeat(args) -> None:
    from src.models.dancedb.sync import sync_onbeat
    sync_onbeat()


def _sync_cogwork(args) -> None:
    from src.models.dancedb.sync import sync_cogwork
    sync_cogwork()


def _sync_folketshus(args) -> None:
    from src.models.dancedb.sync import sync_folketshus
    sync_folketshus()


def _sync_all(args) -> None:
    from src.models.dancedb.sync import sync_all
    month, year = get_month_year(args.month, args.year)
    sync_all(
        month=month,
        year=year,
        limit=args.limit,
        only_scrape=args.only_scrape,
    )


def _scrape_bygdegardarna(args) -> None:
    from src.models.dancedb.venue_ops import scrape_bygdegardarna
    from datetime import date
    date_str = args.date or date.today().strftime("%Y-%m-%d")
    scrape_bygdegardarna(date_str)


def _scrape_dancedb_venues(args) -> None:
    from src.models.dancedb.venue_ops import scrape_dancedb_venues
    date_str = get_date_str(args.date)
    scrape_dancedb_venues(date_str)


def _match_bygdegardarna_venues(args) -> None:
    from src.models.dancedb.venue_ops import match_venues
    date_str = get_date_str(args.date)
    match_venues(date_str, skip_prompts=args.skip_prompts)


def _scrape_folketshus(args) -> None:
    from src.models.folketshus.venue import run as scrape_folketshus
    scrape_folketshus(date_str=args.date)


def _scrape_wikidata_artists(args) -> None:
    from src.models.wikidata.operations import scrape_wikidata_artists
    date_str = get_date_str(args.date)
    scrape_wikidata_artists(date_str)


def _match_wikidata_artists(args) -> None:
    from src.models.wikidata.operations import match_wikidata_artists
    date_str = get_date_str(args.date)
    match_wikidata_artists(date_str)


def _sync_wikidata_artists(args) -> None:
    from src.models.wikidata.operations import sync_wikidata_artists
    date_str = get_date_str(args.date)
    sync_wikidata_artists(date_str, month=args.month, year=args.year)
