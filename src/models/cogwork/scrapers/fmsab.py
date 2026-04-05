import logging

from src.models.cogwork.event import CogworkEvent
from src.models.cogwork.organizer import CogworkOrganizer

logger = logging.getLogger(__name__)


class FmsabEvent(CogworkEvent):
    organizer_qid: str = "Q507"
    dance_style_qid_map: dict = {
        "fox": "Q23",
        "west coast swing": "Q15",
        "modern fox": "Q23",
        "bugg": "Q485",
        "casanovas": "Q4",
        "socialdans": "Q4",
        "bugg": "Q485",
    }
    venue_qid_map: dict[str, str] = {
        "Vallsta bygdegård": "Q508",
        "Åslidens dansloge": "Q46",
    }


class Fmsab(CogworkOrganizer):
    organizer_slug: str = "fmsab"
    event_class: CogworkEvent = FmsabEvent
