"""Shared CLI utilities."""
from datetime import date
from pathlib import Path
from typing import Any


def get_date_str(date_arg: str | None) -> str:
    """Get date string from CLI argument or default to today."""
    return date_arg or date.today().strftime("%Y-%m-%d")


def get_month_year(month_arg: str | None, year_arg: int | None) -> tuple[str, int]:
    """Get month and year from CLI arguments or default to current."""
    if month_arg and year_arg:
        return month_arg, year_arg
    
    from src.models.dancedb.sync_ops import get_current_month_year
    return get_current_month_year()


def get_data_dir() -> Path:
    """Get the data directory path."""
    import config
    return config.data_dir


def ensure_dir(path: Path) -> None:
    """Ensure directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Any:
    """Load JSON file."""
    import json
    return json.loads(path.read_text())


def save_json(data: Any, path: Path, **kwargs) -> None:
    """Save JSON file."""
    import json
    ensure_dir(path.parent)
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, **kwargs)


def add_common_date_parser(parser) -> None:
    """Add common -d/--date argument to parser."""
    parser.add_argument("-d", "--date", default=None, help="Date for output (YYYY-MM-DD, default: today)")


def add_common_month_year_parser(parser) -> None:
    """Add common -m/--month and -y/--year arguments to parser."""
    parser.add_argument("-m", "--month", default=None, help="Month name (default: current month)")
    parser.add_argument("-y", "--year", type=int, default=None, help="Year (default: current year)")
