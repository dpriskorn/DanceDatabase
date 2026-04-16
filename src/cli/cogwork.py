"""Cogwork CLI commands."""


def add_cogwork_subparsers(sub) -> dict:
    """Add cogwork subparsers and return command handlers."""
    handlers = {}
    
    p = sub.add_parser("scrape-cogwork", help="Fetch cogwork events from ALL sources")
    p.add_argument("-s", "--source", default=None, help="Specific source (default: all)")
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing output files")
    handlers["scrape-cogwork"] = _scrape_cogwork
    
    p = sub.add_parser("upload-cogwork", help="Upload cogwork events to DanceDB")
    p.add_argument("-s", "--source", default=None, help="Specific source (default: all)")
    handlers["upload-cogwork"] = _upload_cogwork
    
    return handlers


def _scrape_cogwork(args) -> None:
    from src.models.cogwork.scrape import scrape as scrape_cogwork
    scrape_cogwork(source=args.source, overwrite=args.overwrite)


def _upload_cogwork(args) -> None:
    from src.models.cogwork.upload import upload as upload_cogwork
    upload_cogwork(source=args.source)
