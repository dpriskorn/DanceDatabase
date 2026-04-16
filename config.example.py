import logging
from datetime import timedelta, timezone
from pathlib import Path

loglevel = logging.DEBUG
username = ""
password = ""
user_agent = "DanceDB/1.0 (User:So9q)"

WIKIBASE_URL = "https://dance.wikibase.cloud"
MEDIAWIKI_API_URL = "https://dance.wikibase.cloud/w/api.php"
SPARQL_ENDPOINT_URL = "https://dance.wikibase.cloud/query/sparql"

PROJECT_ROOT = Path(__file__).parent.resolve()

data_dir: Path = PROJECT_ROOT / "data"
bygdegardarna_dir: Path = data_dir / "bygdegardarna"
folketshus_dir: Path = data_dir / "folketshus"
onbeat_dir: Path = data_dir / "onbeat"
dancedb_dir: Path = data_dir / "dancedb"
dancedb_artists_dir: Path = dancedb_dir / "artists"
dancedb_venues_dir: Path = dancedb_dir / "venues"
dancedb_events_dir: Path = dancedb_dir / "events"
danslogen_dir: Path = data_dir / "danslogen"
danslogen_artists_dir: Path = danslogen_dir / "artists"
danslogen_events_dir: Path = danslogen_dir / "events"
wikidata_dir: Path = data_dir / "wikidata"
enrich_dir: Path = data_dir / "bygdegardarna" / "enriched"
folketshus_unmatched_dir: Path = folketshus_dir / "unmatched"
folketshus_enriched_dir: Path = folketshus_dir / "enriched"
bygdegardarna_enriched_dir: Path = bygdegardarna_dir / "enriched"
static_dir: Path = data_dir / "static"

CET = timezone(timedelta(hours=1))

FUZZY_THRESHOLD_VENUE_BYGDEGARDARNA = 90
FUZZY_THRESHOLD_VENUE_DANSLOGEN = 90
FUZZY_THRESHOLD_VENUE_FOLKETSHUS = 95
FUZZY_AUTOMATCH_THRESHOLD_VENUE_FOLKETSHUS = 100
FUZZY_THRESHOLD_VENUE_ONBEAT = 90
FUZZY_THRESHOLD_ARTIST_DANSLOGEN = 90
FUZZY_THRESHOLD_ARTIST_ONBEAT = 90

COORD_MATCH_THRESHOLD_KM = 0.1

FUZZY_REMOVE_TERMS_BYGDEGARDARNA = ["folkets park", "folkets hus", "förening", "gård", "lösa", "arp", "hult"]
FUZZY_REMOVE_TERMS_DANSLOGEN = ["folkets park", "folkets hus", "förening", "gård", "lösa", "arp", "hult"]
FUZZY_REMOVE_TERMS_FOLKETSHUS = ["folkets park", "folkets hus", "förening", "gård", "lösa", "arp", "hult"]
FUZZY_REMOVE_TERMS_ONBEAT = ["folkets park", "folkets hus", "förening", "gård", "lösa", "arp", "hult"]
FUZZY_REMOVE_TERMS_ARTIST_DANSLOGEN = []
FUZZY_REMOVE_TERMS_ARTIST_ONBEAT = []

FUZZY_FALSE_FRIENDS = {
    "alvesta": ["avesta"],
    "avesta": ["alvesta"],
    "landskrona": ["karlskrona"],
    "karlskrona": ["landskrona"],
    "trosa": ["kungälv", "knivsta"],
    "kungälv": ["trosa", "knivsta"],
    "knivsta": ["trosa", "kungälv"],
    "roma": ["romme"],
    "romme": ["roma"],
    "hög": ["högsby"],
    "högsby": ["hög"],
    "ramlösa": ["ramnäs"],
    "ramnäs": ["ramlösa"],
    "sala folkets park": ["sala folkets hus"],
}

SHIP_COORDINATES = {
    "stena": {"lat": 59.31681013367709, "lng": 18.09538237657978},
    "viking": {"lat": 59.31681013367709, "lng": 18.09538237657978},
    "birka": {"lat": 59.31681013367709, "lng": 18.09538237657978},
    "tallink": {"lat": 59.35260329949055, "lng": 18.117075933870833},
}

DANCE_PROP_INSTANCE_OF = "P1"
DANCE_PROP_VENUE = "P5"
DANCE_PROP_START = "P32"
DANCE_PROP_END = "P33"
DANCE_PROP_STATUS = "P43"
DANCE_PROP_ARTIST = "P56"
DANCE_PROP_DANCE_STYLE = "P11"
DANCE_PROP_WIKIDATA = "P3"
DANCE_PROP_COORDINATES = "P4"
DANCE_PROP_BYGDEGARDARNA_ID = "P42"
DANCE_PROP_FOLKETSHUS_ID = "P44"
DANCE_PROP_SPELPLAN_ID = "P46"

DANCE_INSTANCE_EVENT = "Q2"
DANCE_INSTANCE_VENUE = "Q20"
DANCE_INSTANCE_ARTIST = "Q225"
DANCE_STATUS_PLANNED = "Q566"
DANCE_STATUS_CANCELLED = "Q567"
