import logging
from datetime import datetime
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

        start_dt, end_dt = self._parse_datetime(date, time_str)

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
                    dance_styles=[],
                    event_series="",
                    organizer="",
                    event=""
                )
            ),
            last_update=datetime.now().replace(tzinfo=CET, microsecond=0),
            price_late=None,
            price_early=None,
            coordinates=None,
            weekly_recurring=False,
            number_of_occasions=1
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
        date: datetime,
        time_str: str
    ) -> tuple[Optional[datetime], Optional[datetime]]:
        """Parse time string like '18.00-22.00' into start/end datetimes."""
        start_dt = None
        end_dt = None

        if time_str and date:
            try:
                time_clean = time_str.replace('.', ':')
                if '-' in time_clean:
                    start_str, end_str = time_clean.split('-', 1)
                    start_dt = datetime.strptime(
                        f"{date.strftime('%Y-%m-%d')} {start_str.strip()}",
                        "%Y-%m-%d %H:%M"
                    ).replace(tzinfo=CET)
                    end_dt = datetime.strptime(
                        f"{date.strftime('%Y-%m-%d')} {end_str.strip()}",
                        "%Y-%m-%d %H:%M"
                    ).replace(tzinfo=CET)
                else:
                    start_dt = datetime.strptime(
                        f"{date.strftime('%Y-%m-%d')} {time_clean.strip()}",
                        "%Y-%m-%d %H:%M"
                    ).replace(tzinfo=CET)
            except Exception as e:
                logger.warning("Failed to parse time '%s': %s", time_str, e)

        return start_dt, end_dt