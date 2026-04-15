"""Ensure all event venues exist in DanceDB."""
import json
import logging
import sys
from datetime import date
from pathlib import Path

from rapidfuzz import process as fuzz_process

import config
from src.models.dancedb.client import DancedbClient

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
EVENTS_DIR = DATA_DIR / "dancedb" / "events"
ARTISTS_DIR = DATA_DIR / "dancedb" / "artists"


def configure_wbi():
    """Configure wikibase-integrator."""
    from wikibaseintegrator.wbi_config import config as wbi_config
    wbi_config['WIKIBASE_URL'] = 'https://dance.wikibase.cloud'
    wbi_config['MEDIAWIKI_API_URL'] = 'https://dance.wikibase.cloud/w/api.php'
    wbi_config['SPARQL_ENDPOINT_URL'] = 'https://dance.wikibase.cloud/query/sparql'
    wbi_config['USER_AGENT'] = config.user_agent


def run(month: str = "april", year: int = 2026, dry_run: bool = False, save: bool = False) -> list[dict]:
    """Ensure all event venues exist in DanceDB.
    
    Returns list of events fetched from DanceDB.
    Always saves events and artists to JSON files.
    """
    configure_wbi()
    
    print(f"\n=== Ensuring event venues exist for {month} {year} ===")

    events = fetch_events_from_dancedb()
    print(f"Found {len(events)} events in DanceDB")

    EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = date.today().strftime("%Y-%m-%d")
    output_file = EVENTS_DIR / f"{date_str}.json"
    output_file.write_text(json.dumps(events, indent=2, ensure_ascii=False) + "\n")
    print(f"Saved to {output_file}")

    client = DancedbClient()
    artists = client.fetch_artists_from_dancedb()
    print(f"Found {len(artists)} artists in DanceDB")

    ARTISTS_DIR.mkdir(parents=True, exist_ok=True)
    artists_file = ARTISTS_DIR / f"{date_str}.json"
    artists_file.write_text(json.dumps(artists, indent=2, ensure_ascii=False) + "\n")
    print(f"Saved to {artists_file}")

    if save:
        return events

    missing_p7 = []
    venues_needed = {}

    for event in events:
        venue_qid = event.get("venue_qid")
        if not venue_qid:
            missing_p7.append(event["label"])
        else:
            venue_label = event.get("venue_label", "")
            venue_aliases = event.get("venue_aliases", [])
            venue_lower = venue_label.lower()
            if venue_lower in venues_needed:
                if venue_aliases:
                    venues_needed[venue_lower].setdefault("aliases", []).extend(venue_aliases)
            else:
                venues_needed[venue_lower] = {
                    "qid": venue_qid,
                    "label": venue_label,
                    "events": event.get("event_label", ""),
                    "aliases": venue_aliases,
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

        # Check existing venues by aliases
        alias_match = any(
            venue_lower in v.get("aliases", [])
            for v in existing_venues.values()
        )
        if alias_match:
            continue

        # Check event venue aliases
        venue_aliases = venue_info.get("aliases", [])
        if venue_aliases:
            for v in existing_venues.values():
                existing_aliases = v.get("aliases", [])
                if any(a in existing_aliases for a in venue_aliases):
                    alias_match = True
                    break
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
PREFIX dd: <https://dance.wikibase.cloud/entity/>
PREFIX ddt: <https://dance.wikibase.cloud/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX p: <https://dance.wikibase.cloud/prop/>
PREFIX ps: <https://dance.wikibase.cloud/prop/statement/>


SELECT ?event ?eventLabel ?start_date ?venue ?venueLabel WHERE {
    ?event ddt:P1 dd:Q2 .

    OPTIONAL {
        ?event p:P32 ?statement32 .
        ?statement32 ps:P32 ?date32 .
        FILTER(datatype(?date32) = xsd:dateTime || datatype(?date32) = xsd:date)
    }

    # Merge dates
    BIND(COALESCE(?date7, ?date32) AS ?start_date)

    OPTIONAL { ?event rdfs:label ?svLabel FILTER(LANG(?svLabel)="sv") }
    OPTIONAL { ?event rdfs:label ?enLabel FILTER(LANG(?enLabel)="en") }
    BIND(COALESCE(?svLabel, ?enLabel, STR(?event)) AS ?eventLabel)

    OPTIONAL { ?event ddt:P5 ?venue }
    OPTIONAL { ?venue rdfs:label ?svVenueLabel FILTER(LANG(?svVenueLabel)="sv") }
    BIND(COALESCE(?svVenueLabel, "") AS ?venueLabel)
}
    """
    results = execute_sparql_query(query=sparql)
    results = execute_sparql_query(query=sparql)
    events = []

    for binding in results["results"]["bindings"]:
        event_uri = binding.get("event", {}).get("value", "")
        event_label = binding.get("eventLabel", {}).get("value", "")
        start_date = binding.get("start_date", {}).get("value", "")
        
        venue_qid = None
        venue_label = ""
        venue_aliases = []
        venue_binding = binding.get("venue")
        if venue_binding:
            venue_url = venue_binding.get("value", "")
            if venue_url:
                venue_qid = venue_url.rsplit("/", 1)[-1]
                venue_label = binding.get("venueLabel", {}).get("value", "")
                alias_data = binding.get("venueAlias")
                if alias_data:
                    if isinstance(alias_data, list):
                        venue_aliases = [a.get("value", "").lower() for a in alias_data if a.get("value")]
                    else:
                        val = alias_data.get("value", "")
                        if val:
                            venue_aliases = [val.lower()]

        events.append({
            "event_qid": event_uri.rsplit("/", 1)[-1] if event_uri else "",
            "event_label": event_label,
            "start_date": start_date,
            "venue_qid": venue_qid,
            "venue_label": venue_label,
            "venue_aliases": venue_aliases,
        })

    logger.info(f"Fetched {len(events)} events from DanceDB")
    return events


def fetch_existing_venues() -> dict:
    """Fetch existing venues from DanceDB via SPARQL."""
    from wikibaseintegrator.wbi_helpers import execute_sparql_query

    sparql = """
    PREFIX dd: <https://dance.wikibase.cloud/entity/>
    PREFIX ddt: <https://dance.wikibase.cloud/prop/direct/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

    SELECT ?item ?itemLabel (GROUP_CONCAT(?svAlias; SEPARATOR = "|") AS ?aliasStr) WHERE {
      ?item ddt:P1 dd:Q20 .
      OPTIONAL { ?item rdfs:label ?svItemLabel FILTER(LANG(?svItemLabel)="sv") }
      OPTIONAL { ?item skos:altLabel ?svAlias FILTER(LANG(?svAlias)="sv") }
      BIND(COALESCE(?svItemLabel, "") AS ?itemLabel)
    }
    GROUP BY ?item ?itemLabel
    """
    results = execute_sparql_query(query=sparql)
    existing_venues = {}

    for binding in results["results"]["bindings"]:
        qid = binding.get("item", {}).get("value", "").rsplit("/", 1)[-1]
        label = binding.get("itemLabel", {}).get("value", "")

        alias_str = binding.get("aliasStr", {}).get("value", "")
        aliases = [a.lower() for a in alias_str.split("|") if a] if alias_str else []

        label_lower = label.lower()
        if label_lower not in existing_venues:
            existing_venues[label_lower] = {"qid": qid, "aliases": aliases}
        elif aliases:
            existing_venues[label_lower].setdefault("aliases", []).extend(aliases)

    logger.info(f"Fetched {len(existing_venues)} venues from DanceDB")
    return existing_venues