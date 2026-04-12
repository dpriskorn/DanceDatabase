import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from pydantic import AnyUrl, TypeAdapter

from config import CET
from src.models.dance_event import (
    DanceEvent,
    DanceDatabaseIdentifiers,
    EventLinks,
    Identifiers,
    Organizer,
    Registration,
)
from src.models.danslogen.band_mapper import BandMapper
from src.models.danslogen.venue_matcher import VenueMatcher

logger = logging.getLogger(__name__)

AnyUrlAdapter = TypeAdapter(AnyUrl)


class RowParser:
    """Parses danslogen rows to DanceEvent."""

    def __init__(
        self,
        venue_matcher: VenueMatcher,
        band_mapper: BandMapper,
    ):
        self.venue_matcher = venue_matcher
        self.band_mapper = band_mapper

    def parse(self, row: dict, month: str) -> Optional[DanceEvent]:
        """Parse danslogen row dict to DanceEvent.

        Returns None if band/venue not found or date invalid.
        Raises KeyboardInterrupt if venue creation aborted.
        """
        band = row.get('band', '')
        venue = row.get('venue', '') or row.get('ort', '')
        ort = row.get('ort', '')
        day = row.get('day', '')
        time_str = row.get('time', '')
        ovrigt = row.get('ovrigt', '')

        band_qid = self.band_mapper.resolve(band)
        if not band_qid:
            logger.warning("Skipping event for band '%s' - no QID", band)
            return None

        try:
            venue_qid = self.venue_matcher.resolve(venue, ort)
        except KeyboardInterrupt:
            raise

        if not venue_qid:
            logger.warning("Skipping event - no venue QID for '%s'", venue)
            return None

        date = self._parse_date(day, month)
        if not date:
            logger.warning("Skipping event - invalid date %s %s", day, month)
            return None

        start_dt, end_dt = self._parse_datetime(day, month, time_str)

        dance_styles, instance_of = self._detect_dance_styles_and_instance(ovrigt)

        event_id = f"danslogen-{month}-{day}-{band.lower().replace(' ', '-')}"

        organizer = Organizer(
            description="Danslogen",
            official_website=f"https://www.danslogen.se/dansprogram/{month}",
        )

        return DanceEvent(
            id=event_id,
            label={"sv": f"{band} på {venue}"},
            description={"sv": ovrigt},
            location=venue,
            start_timestamp=start_dt,
            end_timestamp=end_dt,
            schedule={},
            price_normal=Decimal(0),
            event_type="dance",
            price_reduced=None,
            links=EventLinks(
                official_website=AnyUrlAdapter.validate_strings(
                    f"https://www.danslogen.se/dansprogram/{month}"
                ),
                sources=[AnyUrlAdapter.validate_strings(
                    f"https://www.danslogen.se/dansprogram/{month}"
                )]
            ),
            organizer=organizer,
            registration=Registration(
                cancelled=False,
                fully_booked=False,
                registration_opens=None,
                registration_closes=None,
                advance_registration_required=False,
                registration_open=False
            ),
            identifiers=Identifiers(
                dancedatabase=DanceDatabaseIdentifiers(
                    source="",
                    venue=venue_qid,
                    dance_styles=dance_styles,
                    event_series="",
                    organizer="",
                    event="",
                    artist=band_qid
                )
            ),
            last_update=datetime.now().replace(tzinfo=CET, microsecond=0),
            price_late=None,
            price_early=None,
            coordinates=None,
            weekly_recurring=False,
            number_of_occasions=1,
            instance_of=instance_of
        )

    def _parse_date(self, day: str, month: str, year: int = 2026) -> Optional[datetime]:
        """Parse day and month name to datetime."""
        month_map = {
            "januari": 1, "februari": 2, "mars": 3, "april": 4,
            "maj": 5, "juni": 6, "juli": 7, "augusti": 8,
            "september": 9, "oktober": 10, "november": 11, "december": 12
        }
        try:
            month_num = month_map.get(month.lower(), 1)
            return datetime.strptime(
                f"{year}-{month_num:02d}-{int(day):02d}",
                "%Y-%m-%d"
            ).replace(tzinfo=CET)
        except Exception:
            return None

    def _parse_datetime(
        self,
        day: str,
        month: str,
        time_str: str,
        year: int = 2026
    ) -> tuple[Optional[datetime], Optional[datetime]]:
        """Parse day, month, time string like '18.00-22.00' into start/end datetimes directly."""
        month_map = {"januari": 1, "februari": 2, "mars": 3, "april": 4,
                  "maj": 5, "juni": 6, "juli": 7, "augusti": 8,
                  "september": 9, "oktober": 10, "november": 11, "december": 12}
        
        try:
            day_num = int(day)
            month_num = month_map.get(month.lower(), 4)
        except (ValueError, TypeError):
            return None, None
        
        if not time_str:
            return None, None
        
        time_clean = time_str.replace('.', ':')
        start_dt = None
        end_dt = None
        
        if "-" in time_clean:
            start_str, end_str = time_clean.split('-', 1)
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

    def _detect_dance_styles_and_instance(self, ovrigt: str) -> tuple[list[str], str]:
        """Detect dance styles from ovrigt field and determine instance type.
        
        Returns (dance_styles list, instance_of QID)
        - SPF → Q675 (dance_styles), Q678 (instance_of - pensionärsdans)
        - PRO → Q676 (dance_styles), Q678 (instance_of - pensionärsdans)
        - länsdans → Q677 (dance_styles), Q677 (instance_of - länsdans)
        """
        dance_styles = []
        instance_of = "Q2"  # default: event
        ovrigt_stripped = ovrigt.strip()
        
        # Check case-sensitive first (SPF, PRO)
        if ovrigt_stripped == "SPF":
            dance_styles.append("Q675")
            instance_of = "Q678"  # pensionärsdans
        elif ovrigt_stripped == "PRO":
            dance_styles.append("Q676")
            instance_of = "Q678"  # pensionärsdans
        
        # Check case-insensitive (länsdans)
        if "länsdans" in ovrigt_stripped.lower():
            if "Q677" not in dance_styles:
                dance_styles.append("Q677")
            instance_of = "Q677"  # länsdans takes precedence
        
        return dance_styles, instance_of