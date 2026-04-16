import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import AnyUrl, TypeAdapter

from config import CET
from src.models._utils.datetime_utils import combine_date_and_time, parse_date
from src.models.danslogen.band_mapper import BandMapper
from src.models.danslogen.venue_matcher import VenueMatcher
from src.models.export.dance_event import DanceDatabaseIdentifiers, DanceEvent, EventLinks, Identifiers, Organizer, Registration

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

    def _parse_date(self, day: str, month: str, year: int = 2026) -> Optional[datetime]:
        return parse_date(day, month, year)

    def _parse_datetime(self, day: str, month: str, time_str: str, year: int = 2026) -> tuple[Optional[datetime], Optional[datetime]]:
        date = parse_date(day, month, year)
        if not date:
            return None, None
        return combine_date_and_time(date, time_str)

    def parse(self, row: dict, month: str) -> Optional[DanceEvent]:
        """Parse danslogen row dict to DanceEvent.

        Returns None if band/venue not found or date invalid.
        Raises KeyboardInterrupt if venue creation aborted.
        """
        band = row.get("band", "")
        venue = row.get("venue", "") or row.get("ort", "")
        ort = row.get("ort", "")
        day = row.get("day", "")
        time_str = row.get("time", "")
        ovrigt = row.get("ovrigt", "")

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

        date = parse_date(day, month)
        if not date:
            logger.warning("Skipping event - invalid date %s %s", day, month)
            return None

        start_dt, end_dt = combine_date_and_time(date, time_str)

        dance_styles, instance_of = self._detect_dance_styles_and_instance(ovrigt)

        event_id = f"danslogen-{month}-{day}-{band.lower().replace(' ', '-')}"

        organizer = Organizer(
            description="",
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
                official_website=AnyUrlAdapter.validate_strings(f"https://www.danslogen.se/dansprogram/{month}"),
                sources=[AnyUrlAdapter.validate_strings(f"https://www.danslogen.se/dansprogram/{month}")],
            ),
            organizer=organizer,
            registration=Registration(
                cancelled=False,
                fully_booked=False,
                registration_opens=None,
                registration_closes=None,
                advance_registration_required=False,
                registration_open=False,
            ),
            identifiers=Identifiers(
                dancedatabase=DanceDatabaseIdentifiers(
                    source="", venue=venue_qid, dance_styles=dance_styles, event_series="", organizer="", event="", artist=band_qid
                )
            ),
            last_update=datetime.now().replace(tzinfo=CET, microsecond=0),
            price_late=None,
            price_early=None,
            coordinates=None,
            weekly_recurring=False,
            number_of_occasions=1,
            instance_of=instance_of,
        )

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

        # Default to bugg och fox (Q4) for regular danslogen events
        if not dance_styles:
            dance_styles = ["Q4"]

        return dance_styles, instance_of
