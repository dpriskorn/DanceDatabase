"""Ensure venues exist in DanceDB.

This module provides venue matching and creation functionality.
Core coordinate-based matching has been moved to ensure_coords.py.
"""
import json
import logging
from datetime import date

from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator.wbi_helpers import execute_sparql_query

import config
from src.models.dancedb.ensure_venues_loader import load_bygdegardarna_venues, load_folketshus_venues, load_bygdegardarna_addresses
from src.models.dancedb.ensure_venue_matcher import match_venue
from src.models.dancedb.ensure_venue_creator import create_venue_interactive
from src.models.dancedb.client import DancedbClient

logger = logging.getLogger(__name__)


def load_existing_venues() -> dict:
    """Load existing venues from DanceDB via SPARQL."""
    wbi_config["User-Agent"] = "DanceDB/1.0 (User:So9q)"

    sparql = """
    PREFIX dd: <https://dance.wikibase.cloud/entity/>
    PREFIX ddt: <https://dance.wikibase.cloud/prop/direct/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

    SELECT ?item ?itemLabel (GROUP_CONCAT(?svAlias; SEPARATOR = "|") AS ?aliasStr) ?geo WHERE {
      ?item ddt:P1 dd:Q20 .
      OPTIONAL { ?item rdfs:label ?itemLabel FILTER(LANG(?itemLabel) = "sv") }
      OPTIONAL { ?item skos:altLabel ?svAlias FILTER(LANG(?svAlias) = "sv") }
      OPTIONAL { ?item ddt:P4 ?geo }
    }
    GROUP BY ?item ?itemLabel ?geo
    ORDER BY ?itemLabel
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
        label_lower = label.lower()
        if label_lower not in venues:
            venues[label_lower] = {"qid": qid, "lat": lat, "lng": lng, "aliases": aliases}
        elif aliases:
            venues[label_lower].setdefault("aliases", []).extend(aliases)

    print(f"Found {len(venues)} existing venues in DanceDB")
    return venues


def load_venue_mappings() -> dict:
    """Load previously saved venue mappings."""
    venue_mappings_file = config.data_dir / "dancedb" / "venue_mappings.jsonl"
    if not venue_mappings_file.exists():
        return {}
    
    print(f"Loading venue mappings from {venue_mappings_file.name}...")
    venues = {}
    with open(venue_mappings_file) as f:
        for line in f:
            if line.strip():
                try:
                    mapping = json.loads(line)
                    name = mapping.get("venue_name", "").lower()
                    qid = mapping.get("qid", "")
                    lat = mapping.get("lat")
                    lng = mapping.get("lng")
                    if name and qid and lat and lng:
                        venues[name] = {"qid": qid, "lat": lat, "lng": lng, "aliases": []}
                except json.JSONDecodeError:
                    continue
    print(f"Loaded {len(venues)} venues (including mappings)")
    return venues


def ensure_venues(date_str: str | None = None) -> None:
    """Ensure danslogen venues exist in DanceDB before uploading events."""
    import sys
    if not sys.stdin.isatty():
        raise RuntimeError("This operation requires an interactive terminal.\nNo TTY detected. Please run interactively.")

    date_str = date_str or date.today().strftime("%Y-%m-%d")
    month_name = date.strptime(date_str, "%Y-%m-%d").strftime("%B").lower()
    print(f"\n=== Ensuring venues exist for {date_str} ===")

    # Load danslogen events
    dansevents_file = config.danslogen_dir / "events" / f"{date_str}-{month_name}.json"
    if not dansevents_file.exists():
        print(f"Error: danslogen data not found: {dansevents_file}")
        return

    events = json.loads(dansevents_file.read_text())
    venues_needed = set(e.get("location") for e in events if e.get("location"))
    print(f"Need venues for {len(venues_needed)} unique locations")

    # Load external venue sources
    bygdegardarna_venues, bygdegardarna_names, bygdegardarna_cities = load_bygdegardarna_venues()
    folketshus_venues, folketshus_names = load_folketshus_venues()
    bygdegardarna_addresses = load_bygdegardarna_addresses()

    # Load existing DanceDB venues
    existing_venues = load_existing_venues()
    existing_venues.update(load_venue_mappings())

    # Process each venue
    venues_list = list(venues_needed)
    total_venues = len(venues_list)
    matched = 0
    matched_auto = 0
    new_venues = []

    for idx, venue_name in enumerate(venues_list):
        remaining = total_venues - idx
        print(f"=== [{idx + 1}/{total_venues}] Remaining: {remaining} ===")

        match_key, match_data = match_venue(
            venue_name=venue_name,
            existing_venues=existing_venues,
            bygdegardarna_venues=bygdegardarna_venues,
            bygdegardarna_names=bygdegardarna_names,
            bygdegardarna_cities=bygdegardarna_cities,
            bygdegardarna_addresses=bygdegardarna_addresses,
            folketshus_venues=folketshus_venues,
            folketshus_names=folketshus_names,
            date_str=date_str,
        )

        if match_key:
            matched += 1
            if match_key in existing_venues and existing_venues[match_key].get("qid"):
                matched_auto += 1
        else:
            new_venues.append(venue_name)

    print(f"Auto-matched (exact): {matched_auto}")
    print(f"Matched (with prompt): {matched}")
    print(f"Need to create: {len(new_venues)}")

    if not new_venues:
        print("All venues exist in DanceDB!")
        return

    print(f"\nMissing venues: {new_venues}")

    # Login to DanceDB
    print("Logging in to DanceDB...")
    db_client = DancedbClient()
    print("Logged in.")

    # Create new venues
    for venue_name in new_venues:
        create_venue_interactive(venue_name, folketshus_venues, folketshus_names, db_client, date_str)

    print("\nVenue matching done. Run 'cli.py upload-events' to process events.")