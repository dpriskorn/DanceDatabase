from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict, condecimal, AnyUrl


# TODO adapt this to schema.org?


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
    dance_styles: list[str] = Field(default_factory=list, description="DanceDatabase QIDs for the dance styles")
    venue: str = Field("", description="DanceDatabase QID for the venue")
    event_series: str = Field("", description="DanceDatabase QID for event series")
    source: str = Field(default_factory=str, description="DanceDatabase QID for data source")


# noinspection PyArgumentList
class Identifiers(BaseModel):
    wikidata: WikidataIdentifiers = WikidataIdentifiers()
    dancedatabase: DanceDatabaseIdentifiers = DanceDatabaseIdentifiers()


class EventLinks(BaseModel):
    facebook: AnyUrl | None = Field(
        default=None,
        description="URL to the event's Facebook page"
    )
    official_website: AnyUrl | None = Field(
        default=None,
        description="URL to the official event website"
    )
    registration_website: AnyUrl | None = Field(
        default=None,
        description="URL to the registration page for the event"
    )
    schedule_website: AnyUrl | None = Field(
        default=None,
        description="URL to the event schedule or timetable"
    )
    venue_website: AnyUrl | None = Field(
        default=None,
        description="URL to the event venue's website"
    )
    image: AnyUrl | None = Field(
        default=None,
        description="URL to an image representing the event"
    )
    sources: list[AnyUrl] = Field(
        default_factory=list,
        description="List of URLs to the source of this event information"
    )


class Registration(BaseModel):
    cancelled: bool = Field(False, description="Whether the event was cancelled at scrape time")
    fully_booked: bool = Field(False, description="Whether it was fully booked at scrape time")
    registration_opens: datetime | None = Field(None, description="When registration opens")
    registration_closes: datetime | None = Field(None, description="When registration closes")
    advance_registration_required: bool = Field(False, description="Whether advance registration is mandatory")
    registration_open: bool = Field(False, description="Whether registration was open at scrape time")


class DanceEvent(BaseModel):
    """Structured representation of a dance event.
    Times are in CEST/CET"""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique identifier for the event")
    # source: str = Field(default_factory=str, description="Source for event")
    label: dict[str, str] = Field(..., description="Language keyed labels")
    description: dict[str, str] = Field(..., description="Language keyed descriptions")
    coordinates: dict[str, float] | None = Field(None, description="Optional coordinates with latitude and longitude")
    schedule: dict[str, Schedule] = Field({}, description="Optional language keyed schedule for the event")
    identifiers: Identifiers = Identifiers()
    links: EventLinks = EventLinks()
    registration: Registration = Registration()
    organizer: Organizer = Field(Organizer(), description="Organizer of the event")

    # time
    last_update: datetime | None = Field(None, description="Timestamp of the last update")
    start_timestamp: datetime | None = Field(None, description="Event start timestamp")
    end_timestamp: datetime | None = Field(None, description="Event end timestamp")
    start_time: str = Field(default_factory=str, description="Event start time, e.g. '10:00'")
    end_time: str = Field(default_factory=str, description="Event end time, e.g. '16:00'")

    # str
    location: str = ""

    # prices
    # todo add currency based on schema.org
    price_early: condecimal(max_digits=10, decimal_places=2) | None = Field(None, description="Early bird price")
    price_normal: condecimal(max_digits=10, decimal_places=2) | None = Field(None, description="Normal price")
    price_late: condecimal(max_digits=10, decimal_places=2) | None = Field(None, description="Late price")

    # bool
    weekly_recurring: bool = False
    number_of_occasions: int = 0
