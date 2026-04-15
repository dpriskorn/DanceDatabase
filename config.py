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

data_dir: Path = Path("data")
bygdegardarna_dir: Path = Path("data/bygdegardarna")
dancedb_dir: Path = Path("data/dancedb")
danslogen_dir: Path = Path("data/danslogen")
wikidata_dir: Path = Path("data/wikidata")
enrich_dir: Path = Path("data/bygdegardarna/enriched")
static_dir: Path = Path("data/static")

CET = timezone(timedelta(hours=1))

# Fuzzy matching threshold (0-100) - higher = stricter matching
FUZZY_THRESHOLD = 90
