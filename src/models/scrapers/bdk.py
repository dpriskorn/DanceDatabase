import logging

from src.models.cogwork.event import CogworkEvent
from src.models.cogwork.organizer import CogworkOrganizer

logger = logging.getLogger(__name__)


class BdkEvent(CogworkEvent):
    organizer_qid: str = "Q61"
    dance_style_qid_map: dict = {
        "fox": "Q23",
        "west coast swing": "Q15",
        "modern fox": "Q23",
        "bugg": "Q485",
        "casanovas": "Q4",
        "socialdans": "Q4"
}
    venue_qid_map: dict[str, str] = {
        "brunnahallen": "Q486",
        "stora salen": "Q486",
        "saldovägen 2": "Q486"
    }


class Bdk(CogworkOrganizer):
    organizer_slug: str = "bdk"
    event_class: CogworkEvent = BdkEvent


