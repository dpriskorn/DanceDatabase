import re
from typing import ClassVar, Optional

from bs4 import Tag
from pydantic import BaseModel, field_validator

from src.models.exceptions import InvalidRowError

TIME_RANGE_PATTERN = re.compile(r'^\d{1,2}\.\d{2}-\d{1,2}\.\d{2}$')
VALID_WEEKDAYS = {'Mån', 'Tis', 'Ons', 'Tor', 'Fre', 'Lör', 'Sön'}


class DanslogenTableRow(BaseModel):
    weekday: str
    day: str
    time: str = ""
    band: str
    venue: str = ""
    ort: str = ""
    kommun: str = ""
    lan: str = ""
    ovrigt: str = ""

    VENUE_KEYWORDS: ClassVar[set[str]] = {'folkets', 'bygdegård', 'bygdegard', 'park', 'kulturhus', 'hallen', 'centrum', 'fritids', 'medborgar'}

    @field_validator('time', mode='before')
    @classmethod
    def parse_time(cls, v):
        if not v or not v.strip():
            return ""
        return v.strip()

    @field_validator('band', mode='before')
    @classmethod
    def validate_band(cls, v):
        if not v or not v.strip():
            raise ValueError("Band cannot be empty")
        return v.strip()

    @field_validator('venue', mode='before')
    @classmethod
    def validate_venue(cls, v):
        if not v or not v.strip():
            return ""
        return v.strip()

    @classmethod
    def _shift_columns_if_venue_empty(cls, venue_val: str, ort_val: str, kommun_val: str, lan_val: str, ovrigt_val: str) -> tuple[str, str, str, str, str]:
        """Handle case where venue cell is empty but next cell contains venue data."""
        if not venue_val and ort_val:
            ort_lower = ort_val.lower()
            if any(keyword in ort_lower for keyword in cls.VENUE_KEYWORDS):
                return ort_val, kommun_val, lan_val, ovrigt_val, ""
        return venue_val, ort_val, kommun_val, lan_val, ovrigt_val

    @classmethod
    def from_row(cls, row: Tag) -> Optional['DanslogenTableRow']:
        cells = row.find_all('td')
        if len(cells) < 9:
            return None

        # Handle rows where first cell is empty (row spans weekday/day from previous)
        if cells[0].get_text(strip=True) == "":
            weekday = cells[1].get_text(strip=True)
            day = cells[2].get_text(strip=True)
            time_val = cells[3].get_text(strip=True)
            band_val = cells[4].get_text(strip=True)
            venue_val = cells[5].get_text(strip=True)
            ort_val = cells[6].get_text(strip=True)
            kommun_val = cells[7].get_text(strip=True)
            lan_val = cells[8].get_text(strip=True)
            ovrigt_val = cells[9].get_text(strip=True) if len(cells) > 9 else ""
        else:
            weekday = cells[0].get_text(strip=True)
            day = cells[1].get_text(strip=True)
            time_val = cells[2].get_text(strip=True)
            band_val = cells[3].get_text(strip=True)
            venue_val = cells[4].get_text(strip=True)
            ort_val = cells[5].get_text(strip=True)
            kommun_val = cells[6].get_text(strip=True)
            lan_val = cells[7].get_text(strip=True)
            ovrigt_val = cells[8].get_text(strip=True)

        venue_val, ort_val, kommun_val, lan_val, ovrigt_val = cls._shift_columns_if_venue_empty(
            venue_val, ort_val, kommun_val, lan_val, ovrigt_val
        )

        if not band_val or not band_val.strip():
            return None

        if TIME_RANGE_PATTERN.match(band_val):
            raise InvalidRowError(
                f"Band field contains time range '{band_val}' - column mapping error. "
                f"Row cells: {[c.get_text(strip=True) for c in cells]}"
            )

        if not day.isdigit():
            raise InvalidRowError(
                f"Day field is not a valid number: '{day}'"
            )

        if weekday and weekday not in VALID_WEEKDAYS:
            raise InvalidRowError(
                f"Weekday '{weekday}' not in valid weekdays: {VALID_WEEKDAYS}"
            )

        return cls(
            weekday=weekday,
            day=day,
            time=time_val,
            band=band_val,
            venue=venue_val,
            ort=ort_val,
            kommun=kommun_val,
            lan=lan_val,
            ovrigt=ovrigt_val
        )
