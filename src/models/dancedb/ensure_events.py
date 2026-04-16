"""Ensure all event venues exist in DanceDB."""

import json
import logging
from datetime import date
from pathlib import Path

import config

logger = logging.getLogger(__name__)


def configure_wbi():
    """Configure wikibase-integrator."""
    from wikibaseintegrator.wbi_config import config as wbi_config

    wbi_config["WIKIBASE_URL"] = "https://dance.wikibase.cloud"
    wbi_config["MEDIAWIKI_API_URL"] = "https://dance.wikibase.cloud/w/api.php"
    wbi_config["SPARQL_ENDPOINT_URL"] = "https://dance.wikibase.cloud/query/sparql"
    wbi_config["USER_AGENT"] = config.user_agent


def fetch_events_from_dancedb(date_str: str | None = None, save: bool = True) -> list[dict]:
    """Fetch all events from DanceDB via SPARQL.
    
    Args:
        date_str: Date string for output file (YYYY-MM-DD, default: today)
        save: Whether to save events to JSON file (default: True)
    
    Returns:
        List of event dicts with qid, label, start_date, venue info
    """
    configure_wbi()
    from wikibaseintegrator.wbi_helpers import execute_sparql_query

    sparql = f"""
PREFIX dd: <https://dance.wikibase.cloud/entity/>
PREFIX ddt: <https://dance.wikibase.cloud/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?event ?eventLabel ?start ?end ?venue ?venueLabel WHERE {{
    ?event ddt:{config.DANCE_PROP_INSTANCE_OF} dd:{config.DANCE_INSTANCE_EVENT} .

    OPTIONAL {{ ?event ddt:{config.DANCE_PROP_START} ?start . }}
    OPTIONAL {{ ?event ddt:{config.DANCE_PROP_END} ?end . }}

    OPTIONAL {{ ?event rdfs:label ?svLabel FILTER(LANG(?svLabel)="sv") }}
    OPTIONAL {{ ?event rdfs:label ?enLabel FILTER(LANG(?enLabel)="en") }}
    BIND(COALESCE(?svLabel, ?enLabel, STR(?event)) AS ?eventLabel)

    OPTIONAL {{ ?event ddt:{config.DANCE_PROP_VENUE} ?venue }}
    OPTIONAL {{ ?venue rdfs:label ?svVenueLabel FILTER(LANG(?svVenueLabel)="sv") }}
    BIND(COALESCE(?svVenueLabel, "") AS ?venueLabel)
}}
    """
    results = execute_sparql_query(query=sparql)
    events = []

    for binding in results["results"]["bindings"]:
        event_uri = binding.get("event", {}).get("value", "")
        event_label = binding.get("eventLabel", {}).get("value", "")
        start_date = binding.get("start", {}).get("value", "")
        end_date = binding.get("end", {}).get("value", "")

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

        events.append(
            {
                "event_qid": event_uri.rsplit("/", 1)[-1] if event_uri else "",
                "event_label": event_label,
                "start_date": start_date,
                "end_date": end_date,
                "venue_qid": venue_qid,
                "venue_label": venue_label,
                "venue_aliases": venue_aliases,
            }
        )

    logger.info(f"Fetched {len(events)} events from DanceDB")
    
    if save and date_str:
        output_file = config.dancedb_events_dir / f"{date_str}.json"
        config.dancedb_events_dir.mkdir(parents=True, exist_ok=True)
        
        unique_events = {}
        for e in events:
            qid = e.get("event_qid")
            if qid and qid not in unique_events:
                unique_events[qid] = e
        
        output = list(unique_events.values())
        output_file.write_text(json.dumps(output, indent=2, ensure_ascii=False))
        logger.info(f"Saved {len(output)} unique events to {output_file}")
    
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
