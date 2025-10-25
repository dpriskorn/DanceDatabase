import logging

from src.models.cogwork.event import CogworkEvent
from src.models.cogwork.organizer import CogworkOrganizer

logger = logging.getLogger(__name__)


class NimbusdkEvent(CogworkEvent):
    skip_sv_labels: list[str] = [
        "Lindy Hop träning",
        "fox träning"
    ]
    organizer_qid: str = "Q161"
    dance_style_qid_map: dict = {
        "fox": "Q23",
        "west coast swing": "Q15",
        "wcs": "Q15",
        "modern fox": "Q23",
        "bugg": "Q485",
        "casanovas": "Q4",
        "socialdans": "Q4",
        "line dance": "Q491",
        "Argentinsk Tango": "Q492",
        "Tango": "Q492"
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
        "Nimbus Dansklubb": "Q161",
        "Gärdesgallerian": "Q161",
        "Bollnäs": "Q161",
        "Lindy Hop Fortsättning Helgkurs": "Q161", #workaround pga ställe saknas
    }


class Nimbusdk(CogworkOrganizer):
    organizer_slug: str = "nimbusdk"
    event_class: CogworkEvent = NimbusdkEvent


