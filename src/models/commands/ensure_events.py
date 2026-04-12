"""Ensure all event venues exist in DanceDB."""
import json
import logging
import sys
from datetime import date
from pathlib import Path

from rapidfuzz import process as fuzz_process

import config
from src.models.dancedb_client import DancedbClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=config.loglevel)

DATA_DIR = Path("data")


def run(month: str = "april", year: int = 2026, dry_run: bool = False) -> None:
    """Ensure all event venues exist in DanceDB.
    
    Args:
        month: Month name (e.g., 'april')
        year: Year (e.g., 2026)
        dry_run: If True, only check without exit code
    """
    print(f"\n=== Ensuring event venues exist for {month} {year} ===")

    events_file = DATA_DIR / f"danslogen_rows_{year}_{month}.json"
    if not events_file.exists():
        print(f"Error: events file not found: {events_file}")
        return

    events = json.loads(events_file.read_text())
    venues_needed = set(e.get("location") for e in events if e.get("location"))
    venues_needed.discard("")
    venues_needed.discard(None)
    venues_needed = sorted(venues_needed)

    print(f"Need venues for {len(venues_needed)} unique locations")

    # Fetch existing venues from DanceDB
    existing_venues = fetch_existing_venues()
    print(f"Found {len(existing_venues)} existing venues in DanceDB")

    # Check all venues exist
    missing = []
    existing_labels = list(existing_venues.keys())

    for venue_name in venues_needed:
        venue_lower = venue_name.lower()

        # Check exact label
        if venue_lower in existing_venues:
            continue

        # Check alias
        alias_match = any(
            venue_lower in v.get("aliases", [])
            for v in existing_venues.values()
        )
        if alias_match:
            continue

        # Check fuzzy (for similar names)
        fuzzy = fuzz_process.extractOne(venue_lower, existing_labels, score_cutoff=90)
        if fuzzy:
            logger.info(f"Fuzzy matched '{venue_name}' to '{fuzzy[0]}' ({fuzzy[1]}%)")
            continue

        missing.append(venue_name)

    if missing:
        print(f"\n=== Missing venues ({len(missing)}) ===")
        for v in missing:
            print(f"  - {v}")
        print(f"\nRun 'python cli.py ensure-venues -d {year}-{month[:3].title()}-01' first to create missing venues.")
        if not dry_run:
            sys.exit(1)

    print(f"\nAll {len(venues_needed)} venues exist in DanceDB.")


def fetch_existing_venues() -> dict:
    """Fetch existing venues from DanceDB via SPARQL."""
    from wikibaseintegrator.wbi_helpers import execute_sparql_query

    sparql = """
    PREFIX dd: <https://dance.wikibase.cloud/entity/>
    PREFIX ddt: <https://dance.wikibase.cloud/prop/direct/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?item ?itemLabel ?alias ?geo WHERE {
      ?item ddt:P1 dd:Q20 .
      OPTIONAL { ?item rdfs:label ?itemLabel FILTER(LANG(?itemLabel) = "sv") }
      OPTIONAL { ?item rdfs:alias ?alias FILTER(LANG(?alias) = "sv") }
      OPTIONAL { ?item ddt:P4 ?geo }
    }
    """
    results = execute_sparql_query(query=sparql)
    existing_venues = {}

    for binding in results["results"]["bindings"]:
        qid = binding["item"]["value"].rsplit("/", 1)[-1]
        label = binding.get("itemLabel", {}).get("value", "")
        alias = binding.get("alias", {}).get("value", "")
        geo = binding.get("geo", {}).get("value", "")

        lat, lng = None, None
        if geo:
            coords = geo.replace("Point(", "").replace(")", "").split(" ")
            lng, lat = float(coords[0]), float(coords[1])

        label_lower = label.lower()
        if label_lower not in existing_venues:
            existing_venues[label_lower] = {"qid": qid, "lat": lat, "lng": lng, "aliases": []}

        if alias:
            existing_venues[label_lower].setdefault("aliases", []).append(alias.lower())

    logger.info(f"Fetched {len(existing_venues)} venues from DanceDB")
    return existing_venues