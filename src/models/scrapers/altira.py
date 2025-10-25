import logging

from src.models.cogwork.event import CogworkEvent
from src.models.cogwork.organizer import CogworkOrganizer

logger = logging.getLogger(__name__)


class AltiraEvent(CogworkEvent):
    skip_sv_labels: list[str] = [
        "träningstid",
        "träningsavgift"
    ]
    organizer_qid: str = "Q71"
    dance_style_qid_map: dict = {
        "fox": "Q23",
        "west coast swing": "Q15",
        "modern fox": "Q23",
        "bugg": "Q485",
        "casanovas": "Q4",
        "socialdans": "Q4"
}
    venue_qid_map: dict[str, str] = {
        "Altiras lokal": "Q71"
    }


class Altira(CogworkOrganizer):
    organizer_slug: str = "altira"
    event_class: CogworkEvent = AltiraEvent


