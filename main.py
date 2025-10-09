import glob
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

from pydantic import BaseModel, Field, ValidationError


class Organizer(BaseModel):
    qid: str = ""
    description: str = ""
    website: str = ""


class EventItem(BaseModel):
    """Represents a single scheduled item like a course, workshop, or social dance.
    Times are in CEST/CET"""
    name: str
    start_time: datetime
    end_time: datetime


class ScheduleDay(BaseModel):
    """Represents the schedule for a single day."""
    date: datetime
    items: List[EventItem] = []


class Schedule(BaseModel):
    """Represents the full schedule for the event."""
    days: List[ScheduleDay] = []


class DanceEvent(BaseModel):
    """Structured representation of a dance event."""
    id: str = Field(..., description="Unique identifier for the event")
    dance_type_qid: Optional[str] = Field(None, description="Wikidata QID for dance type (e.g. Q1057898)")
    start_time_utc: Optional[datetime] = None
    end_time_utc: Optional[datetime] = None
    registration_opens: Optional[datetime] = None
    registration_closes: Optional[datetime] = None
    organizer: Organizer = Organizer()
    label: Dict[str, str] = Field(..., description="Labels in different languages (sv, en)")
    description: Dict[str, str] = Field(..., description="Descriptions in different languages (sv, en)")
    coordinates: Optional[Dict[str, float]] = None
    venue_qid: str = ""
    event_series_qid: str = ""
    facebook_link: str = ""
    website: str = ""
    location: str = ""
    image: str = ""
    price_early: str = ""
    price_normal: str = ""
    price_late: str = ""
    schedule: Optional[Schedule] = None


# ---- Validation script ----
data_folder = Path("data")
json_files = glob.glob(str(data_folder / "*.json"))

for file_path in json_files:
    print(f"Validating {file_path}...")
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            event = DanceEvent(**data)
            print(f"✅ {file_path} is valid.")
        except (ValidationError, json.JSONDecodeError) as e:
            print(f"❌ {file_path} is invalid!")
            print(e)