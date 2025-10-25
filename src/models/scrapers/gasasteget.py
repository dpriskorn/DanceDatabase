import logging

from src.models.cogwork.event import CogworkEvent
from src.models.cogwork.organizer import CogworkOrganizer

logger = logging.getLogger(__name__)


class GasastegetEvent(CogworkEvent):
    skip_sv_labels: list[str] = [
    ]
    organizer_qid: str = "Q493"
    dance_style_qid_map: dict = {
        "fox": "Q23",
        "west coast swing": "Q15",
        "wcs": "Q15",
        "modern fox": "Q23",
        "bugg": "Q485",
        "casanovas": "Q4",
        "socialdans": "Q4",
        "Gillesdanser": "Q496",
        "Boogie Woogie": "Q497"
}
    venue_qid_map: dict[str, str] = {
        "Kvarntorpsgården": "Q136",
        "HällesåkersGården": "Q487",
        "Galaxy i Vallentuna": "Q19",
        "Sägnernas Hus": "Q21",
        "Sala Folkets Park": "Q22",
        "Altiras lokal": "Q71",
        "Matfors folkets hus": "Q488",
        "Danslogen på Norra berget": "Q489",
        "Quality Hotel Strawberry Arena": "Q490",
        "Epic Studios": "Q82",
        "Fågelskolans Gymnastiksal B": "Q494",
        "Kalkstensvägen": "Q495",
        "Gåsalyckan": "Q495",
    }


class Gasasteget(CogworkOrganizer):
    organizer_slug: str = "gasasteget"
    event_class: CogworkEvent = GasastegetEvent


