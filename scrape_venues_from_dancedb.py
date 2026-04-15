import json
import logging
from datetime import date
from pathlib import Path

import config
from src.models.dancedb.client import execute_sparql_query

logging.basicConfig(level=config.loglevel)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("data") / "dancedb" / "venues"


def fetch_venues() -> dict[str, dict]:
    sparql = """
    PREFIX dd: <https://dance.wikibase.cloud/entity/>
    PREFIX ddt: <https://dance.wikibase.cloud/prop/direct/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>

    SELECT ?item ?itemLabel ?geo ?p42 WHERE {
      ?item ddt:P1 dd:Q20 .
      OPTIONAL { ?item rdfs:label ?itemLabel FILTER(LANG(?itemLabel) = "sv") }
      OPTIONAL { ?item ddt:P4 ?geo }
      OPTIONAL { ?item ddt:P42 ?p42 }
    }
    ORDER BY ?itemLabel
    LIMIT 2000
    """
    results = execute_sparql_query(query=sparql)
    venues = {}
    for binding in results["results"]["bindings"]:
        qid = binding["item"]["value"].rsplit("/", 1)[-1]
        label = binding.get("itemLabel", {}).get("value", "")
        geo = binding.get("geo", {}).get("value", "")
        p42 = binding.get("p42", {}).get("value", "")
        lat, lng = None, None
        if geo:
            coords = geo.replace("Point(", "").replace(")", "").split(" ")
            lng, lat = float(coords[0]), float(coords[1])
        venues[qid] = {"label": label, "lat": lat, "lng": lng, "has_p42": bool(p42)}
    return venues


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    today_str = date.today().strftime("%Y-%m-%d")
    output_file = OUTPUT_DIR / f"{today_str}.json"

    print(f"Fetching venues from DanceDB...")
    venues = fetch_venues()
    print(f"Found {len(venues)} venues.")

    output_file.write_text(json.dumps(venues, indent=2, ensure_ascii=False) + "\n")
    print(f"Saved to {output_file}")


if __name__ == "__main__":
    main()
