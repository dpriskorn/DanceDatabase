import glob
import json
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError, ConfigDict


class Organizer(BaseModel):
    description: str = ""
    official_website: str = ""


class EventItem(BaseModel):
    """Represents a single scheduled item like a course, workshop, or social dance.
    Times are in CEST/CET"""
    name: str
    start_time: datetime
    end_time: datetime


class ScheduleDay(BaseModel):
    """Represents the schedule for a single day."""
    date: datetime
    items: list[EventItem] = []


class Schedule(BaseModel):
    """Represents the full schedule for the event."""
    days: list[ScheduleDay] = []


class WikidataIdentifiers(BaseModel):
    """Wikidata does not have compatible items and properties for everything in our model"""
    dance_style: str = Field("", description="Wikidata QID for dance type (e.g. Q1057898)")
    venue: str = Field("", description="Wikidata QID for venue")
    event_series: str = Field("", description="Wikidata QID for event series")


class DanceDatabaseIdentifiers(BaseModel):
    """DanceDatabase should have identifiers for everything in our model, but might not"""
    event: str = Field("", description="DanceDatabase QID for the event")
    organizer: str = Field("", description="DanceDatabase QID for the organizer")
    dance_style: str = Field("", description="DanceDatabase QID for the dance style")
    venue: str = Field("", description="DanceDatabase QID for the venue")
    event_series: str = Field("", description="DanceDatabase QID for event series")


class Identifiers(BaseModel):
    wikidata: WikidataIdentifiers = WikidataIdentifiers()
    dancedatabase: DanceDatabaseIdentifiers = DanceDatabaseIdentifiers()


class DanceEvent(BaseModel):
    """Structured representation of a dance event.
    Times are in CEST/CET"""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique identifier for the event")
    label: dict[str, str] = Field(..., description="Language keyed labels")
    description: dict[str, str] = Field(..., description="Language keyed descriptions")
    coordinates: dict[str, float] | None = Field(None, description="Optional coordinates with latitude and longitude")
    schedule: dict[str, Schedule] = Field({}, description="Optional language keyed schedule for the event")

    # time
    last_update: datetime | None = Field(None, description="Timestamp of the last update")
    start_time: datetime | None = Field(None, description="Event start time")
    end_time: datetime | None = Field(None, description="Event end time")
    registration_opens: datetime | None = Field(None, description="When registration opens")
    registration_closes: datetime | None = Field(None, description="When registration closes")
    organizer: Organizer = Field(Organizer(), description="Organizer of the event")

    # str
    facebook_link: str = ""
    official_website: str = ""
    registration_website: str = ""
    schedule_website: str = ""
    venue_website: str = ""
    location: str = ""
    image: str = ""
    price_early: str = ""
    price_normal: str = ""
    price_late: str = ""

    # bool
    cancelled: bool = False
    fully_booked: bool = False
    weekly_recurring: bool = False
    advance_registration_required: bool = False
    registration_open: bool = False


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