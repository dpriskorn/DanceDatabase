from datetime import datetime, timedelta
from typing import Optional

from config import CET

MONTH_MAP = {
    "januari": 1,
    "februari": 2,
    "mars": 3,
    "april": 4,
    "maj": 5,
    "juni": 6,
    "juli": 7,
    "augusti": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "december": 12,
}

MONTH_NUM_TO_NAME = {v: k for k, v in MONTH_MAP.items()}


def parse_swedish_month(month: str) -> int:
    """Convert Swedish month name to number."""
    return MONTH_MAP.get(month.lower(), 1)


def parse_date(day: str, month: str, year: int = 2026) -> Optional[datetime]:
    """Parse day and Swedish month name to datetime with CET timezone."""
    try:
        month_num = parse_swedish_month(month)
        return datetime.strptime(f"{year}-{month_num:02d}-{int(day):02d}", "%Y-%m-%d").replace(tzinfo=CET)
    except Exception:
        return None


def parse_time_range(time_str: str) -> tuple[str, str]:
    """Parse time range like '18.00-22.00' into (start, end)."""
    if not time_str or time_str.strip() == "":
        return "", ""
    if "-" in time_str:
        start, end = time_str.split("-", 1)
        return start.strip(), end.strip()
    return time_str.strip(), ""


def parse_datetime_range(date_str: str, time_str: str, year: int = 2026) -> tuple[Optional[datetime], Optional[datetime]]:
    """Parse day, month name, time string like '18.00-22.00' into start/end datetimes."""
    month_name = date_str.split()[1] if len(date_str.split()) > 1 else ""
    day = date_str.split()[0] if date_str.split() else ""

    try:
        day_num = int(day)
        month_num = parse_swedish_month(month_name)
    except (ValueError, TypeError):
        return None, None

    if not time_str:
        return None, None

    time_clean = time_str.replace(".", ":")
    start_dt = None
    end_dt = None

    if "-" in time_clean:
        start_str, end_str = time_clean.split("-", 1)
        try:
            start_h, start_m = map(int, start_str.strip().split(":"))
            end_h, end_m = map(int, end_str.strip().split(":"))
        except ValueError:
            return None, None

        start_dt = datetime(year, month_num, day_num, start_h, start_m, tzinfo=CET)
        end_dt = datetime(year, month_num, day_num, end_h, end_m, tzinfo=CET)

        if end_dt.hour <= 3:
            end_dt = end_dt + timedelta(days=1)
    else:
        try:
            start_h, start_m = map(int, time_clean.strip().split(":"))
        except ValueError:
            return None, None

        start_dt = datetime(year, month_num, day_num, start_h, start_m, tzinfo=CET)

    return start_dt, end_dt


def parse_iso_datetime(date_str: str, time_str: Optional[str] = None) -> Optional[datetime]:
    """Parse ISO date string (YYYY-MM-DD) and optional time with CET timezone."""
    if not date_str:
        return None

    try:
        if time_str:
            time_clean = time_str.split()[0]
            dt_str = f"{date_str} {time_clean}"
            return datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=CET)
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=CET)
    except Exception:
        return None


def parse_datetime_with_range(date_str: str, time_str: Optional[str] = None) -> tuple[Optional[datetime], Optional[datetime]]:
    """Parse date and time with range support (e.g., '18:00 - 19:00')."""
    if not date_str:
        return None, None

    try:
        if time_str and " - " in time_str:
            start_str, end_str = [t.strip() for t in time_str.split(" - ", 1)]
            start_date = datetime.strptime(f"{date_str} {start_str}", "%Y-%m-%d %H:%M").replace(tzinfo=CET)
            end_date = datetime.strptime(f"{date_str} {end_str}", "%Y-%m-%d %H:%M").replace(tzinfo=CET)
            return start_date, end_date
        elif time_str:
            start_date = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=CET)
            return start_date, None
        else:
            start_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=CET)
            return start_date, None
    except Exception:
        return None, None


def combine_date_and_time(date: datetime, time_str: str, year: int = 2026) -> tuple[Optional[datetime], Optional[datetime]]:
    """Combine a date with a time range string like '18.00-22.00' or '22:00'."""
    if not time_str or time_str.strip() == "":
        return None, None

    time_clean = time_str.replace(".", ":")
    start_dt = None
    end_dt = None

    if "-" in time_clean:
        start, end = time_clean.split("-", 1)
        try:
            start_h, start_m = map(int, start.strip().split(":"))
            end_h, end_m = map(int, end.strip().split(":"))
        except ValueError:
            return None, None

        start_dt = datetime(date.year, date.month, date.day, start_h, start_m, tzinfo=CET)
        end_dt = datetime(date.year, date.month, date.day, end_h, end_m, tzinfo=CET)

        if end_dt.hour <= 3:
            end_dt = end_dt + timedelta(days=1)
    else:
        try:
            start_h, start_m = map(int, time_clean.strip().split(":"))
        except ValueError:
            return None, None

        start_dt = datetime(date.year, date.month, date.day, start_h, start_m, tzinfo=CET)

    return start_dt, end_dt
