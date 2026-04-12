from pydantic import BaseModel
from pathlib import Path


class DanceDBConfig(BaseModel):
    """Configuration for DanceDB operations."""

    wikibase_url: str = "https://dance.wikibase.cloud"
    api_url: str = "https://dance.wikibase.cloud/w/api.php"
    sparql_url: str = "https://dance.wikibase.cloud/query/sparql"

    data_dir: Path = Path("data")
    bygdegardarna_dir: Path = Path("data/bygdegardarna")
    dancedb_dir: Path = Path("data/dancedb")
    danslogen_dir: Path = Path("data/danslogen")
    enrich_dir: Path = Path("data/bygdegardarna/enriched")

    date_str: str = "2026-04-01"
    month: str = "april"
    year: int = 2026


config = DanceDBConfig()