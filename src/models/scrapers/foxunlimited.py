import logging

from src.models.cogwork.event import CogworkEvent
from src.models.cogwork.organizer import CogworkOrganizer

logger = logging.getLogger(__name__)


class FoxunlimitedEvent(CogworkEvent):
    skip_sv_labels: list[str] = [
    ]
    organizer_qid: str = "Q357"
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
        "HällesåkersGården": "Q487",
        "Galaxy i Vallentuna": "Q19",
        "Sägnernas Hus": "Q21",
        "Sala Folkets Park": "Q22",
        "Altiras lokal": "Q71",
        "Matfors folkets hus": "Q488",
        "Danslogen på Norra berget": "Q489"
    }


class Foxunlimited(CogworkOrganizer):
    organizer_slug: str = "foxunlimited"
    event_class: CogworkEvent = FoxunlimitedEvent


