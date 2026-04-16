"""Scrape venues from various sources."""
import json
import logging
from datetime import date

from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator.wbi_helpers import execute_sparql_query

import config
from src.models.bygdegardarna.scrape import scrape

logger = logging.getLogger(__name__)


def scrape_bygdegardarna(date_str: str | None = None) -> None:
    """Fetch venues from bygdegardarna.se with coordinates."""
    date_str = date_str or date.today().strftime("%Y-%m-%d")
    print("\n=== Scrape bygdegardarna venues ===")

    venues = scrape()
    print(f"Found {len(venues)} venues")

    output_file = config.bygdegardarna_dir / f"{date_str}.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(venues, f, ensure_ascii=False, indent=2)

    print(f"Saved to {output_file}")


def scrape_dancedb_venues(date_str: str | None = None) -> None:
    """Fetch existing venues from DanceDB via SPARQL."""
    date_str = date_str or date.today().strftime("%Y-%m-%d")
    print("\n=== Scrape DanceDB venues ===")

    sparql = """
    PREFIX dd: <https://dance.wikibase.cloud/entity/>
    PREFIX ddt: <https://dance.wikibase.cloud/prop/direct/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

    SELECT ?item ?itemLabel (GROUP_CONCAT(?svAlias; SEPARATOR = "|") AS ?aliasStr) ?geo WHERE {
      ?item ddt:P1 dd:Q20 .
      OPTIONAL { ?item rdfs:label ?svLabel FILTER(LANG(?svLabel) = "sv") }
      OPTIONAL { ?item skos:altLabel ?svAlias FILTER(LANG(?svAlias) = "sv") }
      OPTIONAL { ?item ddt:P4 ?geo }
      BIND(COALESCE(?svLabel, "") AS ?itemLabel)
    }
    GROUP BY ?item ?itemLabel ?geo
    ORDER BY ?itemLabel
    LIMIT 2000
    """
    results = execute_sparql_query(query=sparql)
    venues = {}
    for binding in results["results"]["bindings"]:
        qid = binding["item"]["value"].rsplit("/", 1)[-1]
        label = binding.get("itemLabel", {}).get("value", "")

        alias_str = binding.get("aliasStr", {}).get("value", "")
        aliases = [a.lower() for a in alias_str.split("|") if a] if alias_str else []

        geo = binding.get("geo", {}).get("value", "")
        lat, lng = None, None
        if geo:
            coords = geo.replace("Point(", "").replace(")", "").split(" ")
            lng, lat = float(coords[0]), float(coords[1])

        venue_data = {"label": label, "lat": lat, "lng": lng, "aliases": aliases}
        venues[qid] = venue_data

    print(f"Found {len(venues)} venues")

    output_file = config.dancedb_dir / "venues" / f"{date_str}.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(venues, f, ensure_ascii=False, indent=2)

    print(f"Saved to {output_file}")
