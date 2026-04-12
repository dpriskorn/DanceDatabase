"""Ensure all event venues exist in DanceDB."""
import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path

from rapidfuzz import process as fuzz_process

import config
from src.models.dancedb_client import DancedbClient

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")

def configure_wbi():
    """Configure wikibase-integrator."""
    from wikibaseintegrator.wbi_config import config as wbi_config
    wbi_config['WIKIBASE_URL'] = 'https://dance.wikibase.cloud'
    wbi_config['MEDIAWIKI_API_URL'] = 'https://dance.wikibase.cloud/w/api.php'
    wbi_config['SPARQL_ENDPOINT_URL'] = 'https://dance.wikibase.cloud/query/sparql'
    wbi_config['USER_AGENT'] = config.user_agent


def run(month: str = "april", year: int = 2026, dry_run: bool = False) -> None:
    """Ensure all event venues exist in DanceDB."""
    configure_wbi()
    logging.basicConfig(level=config.loglevel)
    
    print(f"\n=== Ensuring event venues exist for {month} {year} ===")

    events = fetch_events_from_dancedb()
    print(f"Found {len(events)} events in DanceDB")

    missing_p7 = []
    venues_needed = {}

    for event in events:
        venue_qid = event.get("venue_qid")
        if not venue_qid:
            missing_p7.append(event["label"])
        else:
            venue_label = event.get("venue_label", "")
            venues_needed[venue_label.lower()] = {
                "qid": venue_qid,
                "label": venue_label,
                "events": event.get("event_label", ""),
            }

    if missing_p7:
        print(f"\n=== Events missing P7 ({len(missing_p7)}) ===")
        for e in missing_p7:
            print(f"  - {e}")
        print("\nABORTING: All events must have a venue (P7)")
        sys.exit(1)

    print(f"Need venues for {len(venues_needed)} unique locations")

    existing_venues = fetch_existing_venues()
    print(f"Found {len(existing_venues)} existing venues in DanceDB")

    existing_labels = list(existing_venues.keys())
    missing = []

    for venue_lower, venue_info in venues_needed.items():
        if venue_lower in existing_venues:
            continue

        alias_match = any(
            venue_lower in v.get("aliases", [])
            for v in existing_venues.values()
        )
        if alias_match:
            continue

        fuzzy = fuzz_process.extractOne(venue_lower, existing_labels, score_cutoff=90)
        if fuzzy:
            logger.info(f"Fuzzy matched '{venue_info['label']}' to '{fuzzy[0]}' ({fuzzy[1]}%)")
            continue

        missing.append(venue_info["label"])

    if missing:
        print(f"\n=== Missing venues ({len(missing)}) ===")
        for v in missing:
            print(f"  - {v}")
        year_month = f"{year}-{month[:3].title()}-01"
        print(f"\nRun 'python cli.py ensure-venues -d {year_month}' first to create missing venues.")
        sys.exit(1)

    print(f"\nAll {len(venues_needed)} venues exist in DanceDB.")


def fetch_events_from_dancedb() -> list[dict]:
    """Fetch all events from DanceDB via SPARQL."""
    from wikibaseintegrator.wbi_helpers import execute_sparql_query

    sparql = """
    SELECT ?event ?eventLabel ?venue ?venueLabel WHERE { 
      ?event <https://dance.wikibase.cloud/prop/direct/P1> <https://dance.wikibase.cloud/entity/Q2> .
      OPTIONAL { ?event <http://www.w3.org/2000/01/rdf-schema#label> ?el FILTER(LANG(?el) = "sv") }
      OPTIONAL { ?event <https://dance.wikibase.cloud/prop/direct/P7> ?venue }
      OPTIONAL { ?venue <http://www.w3.org/2000/01/rdf-schema#label> ?vl FILTER(LANG(?vl) = "sv") }
      BIND(COALESCE(?el, "") AS ?eventLabel)
      BIND(COALESCE(?vl, "") AS ?venueLabel)
    } LIMIT 100
    """
    results = execute_sparql_query(query=sparql)
    events = []

    for binding in results["results"]["bindings"]:
        event_uri = binding.get("event", {}).get("value", "")
        event_label = binding.get("eventLabel", {}).get("value", "")
        
        venue_qid = None
        venue_label = ""
        venue_binding = binding.get("venue")
        if venue_binding:
            venue_url = venue_binding.get("value", "")
            if venue_url:
                venue_qid = venue_url.rsplit("/", 1)[-1]
                venue_label = binding.get("venueLabel", {}).get("value", "")

        events.append({
            "event_qid": event_uri.rsplit("/", 1)[-1] if event_uri else "",
            "event_label": event_label,
            "venue_qid": venue_qid,
            "venue_label": venue_label,
        })

    logger.info(f"Fetched {len(events)} events from DanceDB")
    return events


def fetch_existing_venues() -> dict:
    """Fetch existing venues from DanceDB via SPARQL."""
    from wikibaseintegrator.wbi_helpers import execute_sparql_query

    sparql = """
    SELECT ?item ?itemLabel ?alias ?geo WHERE { 
      ?item <https://dance.wikibase.cloud/prop/direct/P1> <https://dance.wikibase.cloud/entity/Q20> .
      OPTIONAL { ?item <http://www.w3.org/2000/01/rdf-schema#label> ?itemLabel }
      OPTIONAL { ?item <http://www.w3.org/2000/01/rdf-schema#label> ?alias }
      OPTIONAL { ?item <https://dance.wikibase.cloud/prop/direct/P4> ?geo }
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