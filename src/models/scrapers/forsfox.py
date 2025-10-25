import logging

from src.models.cogwork.event import CogworkEvent
from src.models.cogwork.organizer import CogworkOrganizer

logger = logging.getLogger(__name__)


class ForsfoxEvent(CogworkEvent):
    skip_sv_labels: list[str] = [
    ]
    organizer_qid: str = "Q355"
    dance_style_qid_map: dict = {
        "fox": "Q23",
        "west coast swing": "Q15",
        "modern fox": "Q23",
        "bugg": "Q485",
        "casanovas": "Q4",
        "socialdans": "Q4"
}
    venue_qid_map: dict[str, str] = {
        "Kvarntorpsgården": "Q136",
        "HällesåkersGården": "Q487"
    }


class Forsfox(CogworkOrganizer):
    organizer_slug: str = "forsfox"
    event_class: CogworkEvent = ForsfoxEvent


