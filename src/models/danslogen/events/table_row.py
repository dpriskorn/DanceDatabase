import json
import re
from pathlib import Path
from typing import ClassVar, Optional

from bs4 import Tag
from pydantic import BaseModel, field_validator

from src.models.exceptions import InvalidRowError

TIME_RANGE_PATTERN = re.compile(r"^\d{1,2}[:\.]\d{2}-\d{1,2}[:\.]\d{2}$")
VALID_WEEKDAYS = {"Mån", "Tis", "Ons", "Tor", "Fre", "Lör", "Sön"}

STATIC_DIR = Path("data/static")

MUNICIPALITIES: set[str] = set()
COUNTIES: set[str] = set()
SHIPS: set[str] = set()
URBAN_AREAS: dict[str, str] = {}


def _load_static_data() -> None:
    global MUNICIPALITIES, COUNTIES, SHIPS, URBAN_AREAS

    if MUNICIPALITIES:
        return

    static_dir = STATIC_DIR

    municipalities_file = static_dir / "municipalities.json"
    if municipalities_file.exists():
        MUNICIPALITIES = set(json.loads(municipalities_file.read_text()))

    counties_file = static_dir / "counties.json"
    if counties_file.exists():
        COUNTIES = set(json.loads(counties_file.read_text()))

    ships_file = static_dir / "ships.json"
    if ships_file.exists():
        SHIPS = set(json.loads(ships_file.read_text()))

    urban_areas_file = static_dir / "urban_areas.json"
    if urban_areas_file.exists():
        urban_areas_list = json.loads(urban_areas_file.read_text())
        URBAN_AREAS = {item["label"]: item["qid"] for item in urban_areas_list}


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
    cancelled: bool = False
    venue_qid: Optional[str] = None

    VENUE_KEYWORDS: ClassVar[set[str]] = {
        "folkets",
        "bygdegård",
        "bygdegard",
        "park",
        "kulturhus",
        "hallen",
        "centrum",
        "fritids",
        "medborgar",
        "gården",
        "gatan",
        "plats",
        "bygg",
        "kyrkan",
        "salen",
        "staden",
        "hemmet",
        "våningen",
        "hus",
    }

    @field_validator("time", mode="before")
    @classmethod
    def parse_time(cls, v):
        if not v or not v.strip():
            return ""
        return v.strip()

    @field_validator("band", mode="before")
    @classmethod
    def validate_band(cls, v):
        if not v or not v.strip():
            raise ValueError("Band cannot be empty")
        return v.strip()

    @field_validator("venue", mode="before")
    @classmethod
    def validate_venue(cls, v):
        if not v or not v.strip():
            return ""
        return v.strip()

    @classmethod
    def _is_cancelled(cls, cells: list[str]) -> bool:
        for cell in cells:
            cell_lower = cell.lower()
            if any(term in cell_lower for term in ["inställt", "avbokat", "ställt in", "inställda"]):
                return True
        return False

    @classmethod
    def _get_venue_qid(cls, venue: str) -> Optional[str]:
        if venue in URBAN_AREAS:
            return URBAN_AREAS[venue]
        return None

    @classmethod
    def _classify_content(cls, value: str) -> str:
        if not value:
            return "empty"

        value_stripped = value.strip()

        if TIME_RANGE_PATTERN.match(value_stripped):
            return "time"

        if value_stripped in SHIPS:
            return "ship"

        if value_stripped in COUNTIES:
            return "lan"

        for county in COUNTIES:
            if value_stripped.lower() == county.lower():
                return "lan"

        if value_stripped in MUNICIPALITIES or value_stripped in URBAN_AREAS:
            return "ort"

        value_lower = value_stripped.lower()
        if any(keyword in value_lower for keyword in cls.VENUE_KEYWORDS):
            return "venue"

        return "unknown"

    @classmethod
    def from_row(cls, row: Tag) -> Optional["DanslogenTableRow"]:
        cells = row.find_all("td")

        if len(cells) < 6:
            return None

        _load_static_data()

        if cells[0].get_text(strip=True) == "":
            weekday = cells[1].get_text(strip=True)
            day = cells[2].get_text(strip=True)
            content_cells = cells[3:10]
        else:
            weekday = cells[0].get_text(strip=True)
            day = cells[1].get_text(strip=True)
            content_cells = cells[2:10]

        cell_texts = [c.get_text(strip=True) for c in cells]
        cancelled = cls._is_cancelled(cell_texts)

        if not day.isdigit():
            raise InvalidRowError(f"Day field is not a valid number: '{day}'")

        if weekday and weekday not in VALID_WEEKDAYS:
            raise InvalidRowError(
                f"Weekday '{weekday}' not in valid weekdays: {VALID_WEEKDAYS}"
            )

        time_val = ""
        band_val = ""
        venue_val = ""
        ort_val = ""
        kommun_val = ""
        lan_val = ""
        ovrigt_val = ""

        field_names = ["time", "band", "venue", "ort", "kommun", "lan", "ovrigt"]
        i = 0

        for cell in content_cells:
            content = cell.get_text(strip=True)

            if i >= len(field_names):
                break

            field_type = field_names[i]

            if not content:
                i += 1
                continue

            content_type = cls._classify_content(content)

            if field_type == "band":
                band_val = content
            elif field_type == "time":
                if content_type == "time" and not time_val:
                    time_val = content
                else:
                    band_val = content
            elif field_type == "venue":
                if not venue_val:
                    venue_val = content
                elif not ort_val:
                    ort_val = content
            elif field_type == "ort":
                if not ort_val:
                    ort_val = content
                elif not kommun_val:
                    kommun_val = content
            elif field_type == "kommun":
                if not kommun_val:
                    kommun_val = content
                elif not lan_val:
                    lan_val = content
            elif field_type == "lan":
                lan_val = content
            elif field_type == "ovrigt":
                ovrigt_val = content

            i += 1

        if not band_val or not band_val.strip():
            return None

        if TIME_RANGE_PATTERN.match(band_val):
            raise InvalidRowError(
                f"Band field contains time range '{band_val}' - column mapping error. "
                f"Row cells: {[c.get_text(strip=True) for c in cells]}"
            )

        venue = venue_val or ort_val
        venue_qid = cls._get_venue_qid(venue) if venue else None

        return cls(
            weekday=weekday,
            day=day,
            time=time_val,
            band=band_val,
            venue=venue_val,
            ort=ort_val,
            kommun=kommun_val,
            lan=lan_val,
            ovrigt=ovrigt_val,
            cancelled=cancelled,
            venue_qid=venue_qid,
        )