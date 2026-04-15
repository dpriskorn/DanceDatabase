import logging
import os
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

# Fuzzy matching threshold (0-100) - higher = stricter matching
FUZZY_THRESHOLD = 90
