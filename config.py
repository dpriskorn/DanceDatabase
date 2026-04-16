import logging
from datetime import timedelta, timezone
from pathlib import Path

loglevel = logging.DEBUG
username = "Maintenance@maintenance-bot"
password = "duff6etuvoq1unjosoo1b8lkaot1gqcb"
user_agent = "DanceDB/1.0 (User:So9q)"

WIKIBASE_URL = "https://dance.wikibase.cloud"
MEDIAWIKI_API_URL = "https://dance.wikibase.cloud/w/api.php"
SPARQL_ENDPOINT_URL = "https://dance.wikibase.cloud/query/sparql"

PROJECT_ROOT = Path(__file__).parent.resolve()

data_dir: Path = PROJECT_ROOT / "data"
bygdegardarna_dir: Path = data_dir / "bygdegardarna"
dancedb_dir: Path = data_dir / "dancedb"
danslogen_dir: Path = data_dir / "danslogen"
wikidata_dir: Path = data_dir / "wikidata"
enrich_dir: Path = data_dir / "bygdegardarna" / "enriched"
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
