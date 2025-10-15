import logging

from src.models.cogwork.event import CogworkEvent
from src.models.cogwork.organizer import CogworkOrganizer

logger = logging.getLogger(__name__)


class DansgladjeEvent(CogworkEvent):
    dance_style_qid: str = "Q23"
    organizer_qid: str = "Q24"
    venue_qid_map: dict[str, str] = {
        "Galaxy i Vallentuna": "Q19",
        "Sägnernas Hus": "Q21",
        "Sala Folkets Park": "Q22",
    }


class Dansgladje(CogworkOrganizer):
    organizer_slug: str = "dansgladje"
    event_class: CogworkEvent = DansgladjeEvent


