"""Wikidata urban areas scraper."""

import json
import logging
from datetime import date

from wikibaseintegrator.wbi_config import config as wbi_config

import config as root_config

logger = logging.getLogger(__name__)

WIKIDATA_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"


def _get_wbi_config():
    wbi_config["USER_AGENT"] = root_config.user_agent
    return wbi_config

SPARQL_URBAN_AREAS = """
SELECT ?o ?oLabel WHERE {
    ?o wdt:P31 wd:Q12813115.
    SERVICE wikibase:label { bd:serviceParam wikibase:language "sv". }
}
LIMIT 5000
"""


def scrape_wikidata_urban_areas(date_str: str | None = None) -> dict[str, str]:
    """Fetch Swedish urban areas (tatort) from Wikidata."""
    from wikibaseintegrator.wbi_helpers import execute_sparql_query

    _get_wbi_config()

    date_str = date_str or date.today().strftime("%Y-%m-%d")
    print("\n=== Scrape Wikidata urban areas ===")

    results = execute_sparql_query(query=SPARQL_URBAN_AREAS, endpoint=WIKIDATA_SPARQL_ENDPOINT)

    urban_areas = {}
    for binding in results["results"]["bindings"]:
        qid = binding["o"]["value"].rsplit("/", 1)[-1]
        label = binding.get("oLabel", {}).get("value", "")
        if label:
            urban_areas[label] = qid

    print(f"Found {len(urban_areas)} urban areas")

    output_file = root_config.static_dir / "urban_areas.json"
    urban_areas_list = [{"label": label, "qid": qid} for label, qid in urban_areas.items()]
    with open(output_file, "w") as f:
        json.dump(urban_areas_list, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(urban_areas_list)} urban areas to {output_file}")
    return urban_areas


if __name__ == "__main__":
    scrape_wikidata_urban_areas()