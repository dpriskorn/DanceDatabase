from enum import Enum


class EventType(str, Enum):
    DANCE = "dance"
    MEETING = "meeting"
    UNKNOWN = "unknown"
