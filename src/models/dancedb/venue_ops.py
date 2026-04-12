"""Venue operations: scrape, match, ensure exist."""
import json
import logging
from datetime import date
from pathlib import Path

from src.models.dancedb.config import config
from src.models.dancedb_client import DancedbClient
from src.models.bygdegardarna import fetch_markerdata
from src.models.danslogen.maps import VENUE_QID_MAP, fuzzy_match_qid

logger = logging.getLogger(__name__)

FUZZY_THRESHOLD = 85


def create_venue(venue_name: str, lat: float, lng: float) -> str | None:
    """Create a new venue in DanceDB."""
    client = DancedbClient()
    return client.create_venue(venue_name=venue_name, lat=lat, lng=lng)


def scrape_bygdegardarna(date_str: str | None = None) -> None:
    """Fetch venues from bygdegardarna.se with coordinates."""
    date_str = date_str or date.today().strftime("%Y-%m-%d")
    print(f"\n=== Scrape bygdegardarna venues ===")

    venues = fetch_markerdata()
    print(f"Found {len(venues)} venues")

    output_file = config.bygdegardarna_dir / f"{date_str}.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(venues, f, ensure_ascii=False, indent=2)

    print(f"Saved to {output_file}")


def scrape_dancedb_venues(date_str: str | None = None) -> None:
    """Fetch existing venues from DanceDB via SPARQL."""
    import json
    from wikibaseintegrator.wbi_helpers import execute_sparql_query

    date_str = date_str or date.today().strftime("%Y-%m-%d")
    print(f"\n=== Scrape DanceDB venues ===")

    sparql = """
    PREFIX dd: <https://dance.wikibase.cloud/entity/>
    PREFIX ddt: <https://dance.wikibase.cloud/prop/direct/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?item ?itemLabel ?geo WHERE {
      ?item ddt:P1 dd:Q20 .
      OPTIONAL { ?item rdfs:label ?itemLabel FILTER(LANG(?itemLabel) = "sv") }
      OPTIONAL { ?item ddt:P4 ?geo }
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
        lat, lng = None, None
        if geo:
            coords = geo.replace("Point(", "").replace(")", "").split(" ")
            lng, lat = float(coords[0]), float(coords[1])
        venues[qid] = {"label": label, "lat": lat, "lng": lng}

    print(f"Found {len(venues)} venues")

    output_file = config.dancedb_dir / "venues" / f"{date_str}.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(venues, f, ensure_ascii=False, indent=2)

    print(f"Saved to {output_file}")


def match_venues(date_str: str | None = None, skip_prompts: bool = False) -> None:
    """Match bygdegardarna venues to DanceDB."""
    date_str = date_str or date.today().strftime("%Y-%m-%d")
    print(f"\n=== Match venues to DanceDB ===")

    byg_path = config.bygdegardarna_dir / f"{date_str}.json"
    db_path = config.dancedb_dir / "venues" / f"{date_str}.json"

    if not byg_path.exists():
        print(f"Error: bygdegardarna data not found: {byg_path}")
        return

    if not db_path.exists():
        print(f"Error: DanceDB venues not found: {db_path}")
        return

    byg_venues = json.loads(byg_path.read_text())
    db_venues = json.loads(db_path.read_text())

    db_labels = {v["label"].lower(): qid for qid, v in db_venues.items()}

    enriched = []
    unmatched = []
    matched_count = 0

    for venue in byg_venues:
        title = venue.get("title", "")
        title_lower = title.lower()

        if title_lower in db_labels:
            venue["qid"] = db_labels[title_lower]
            enriched.append(venue)
            matched_count += 1
        else:
            fuzzy = fuzzy_match_qid(title, db_labels)
            if fuzzy and fuzzy[2] >= FUZZY_THRESHOLD:
                venue["qid"] = fuzzy[1]
                enriched.append(venue)
                matched_count += 1
                logger.info(f"Fuzzy matched '{title}' to '{fuzzy[0]}' (score={fuzzy[2]})")
            else:
                unmatched.append(venue)

    print(f"Matched: {matched_count} venues")
    print(f"Unmatched: {len(unmatched)} venues")

    enriched_file = config.enrich_dir / f"{date_str}.json"
    enriched_file.parent.mkdir(parents=True, exist_ok=True)
    with open(enriched_file, "w") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)

    unmatched_file = config.bygdegardarna_dir / "unmatched" / f"{date_str}.json"
    unmatched_file.parent.mkdir(parents=True, exist_ok=True)
    with open(unmatched_file, "w") as f:
        json.dump(unmatched, f, ensure_ascii=False, indent=2)

    print(f"Saved to {enriched_file}")


def ensure_venues(date_str: str | None = None, dry_run: bool = False) -> None:
    """Ensure danslogen venues exist in DanceDB before uploading events."""
    import questionary

    from datetime import datetime
    date_str = date_str or date.today().strftime("%Y-%m-%d")
    month_name = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B").lower()
    print(f"\n=== Ensuring venues exist for {date_str} ===")

    dansevents_file = config.data_dir / f"danslogen_rows_{date_str[:4]}_{month_name}.json"
    if not dansevents_file.exists():
        print(f"Error: danslogen data not found: {dansevents_file}")
        return

    from src.models.danslogen.venue_matcher import VenueMatcher
    from wikibaseintegrator.wbi_helpers import execute_sparql_query

    sparql = """
    PREFIX dd: <https://dance.wikibase.cloud/entity/>
    PREFIX ddt: <https://dance.wikibase.cloud/prop/direct/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?item ?itemLabel ?geo WHERE {
      ?item ddt:P1 dd:Q20 .
      OPTIONAL { ?item rdfs:label ?itemLabel FILTER(LANG(?itemLabel) = "sv") }
      OPTIONAL { ?item ddt:P4 ?geo }
    }
    """
    results = execute_sparql_query(query=sparql)
    existing_venues = {}
    for binding in results["results"]["bindings"]:
        qid = binding["item"]["value"].rsplit("/", 1)[-1]
        label = binding.get("itemLabel", {}).get("value", "")
        geo = binding.get("geo", {}).get("value", "")
        lat, lng = None, None
        if geo:
            coords = geo.replace("Point(", "").replace(")", "").split(" ")
            lng, lat = float(coords[0]), float(coords[1])
        existing_venues[label.lower()] = {"qid": qid, "lat": lat, "lng": lng}

    print(f"Found {len(existing_venues)} existing venues in DanceDB")

    events = json.loads(dansevents_file.read_text())
    venues_needed = set(e.get("location") for e in events if e.get("location"))
    print(f"Need venues for {len(venues_needed)} unique locations")

    new_venues = []
    matched = 0
    for venue_name in venues_needed:
        if venue_name.lower() in existing_venues:
            matched += 1
        else:
            new_venues.append(venue_name)

    print(f"Matched: {matched}")
    print(f"Need to create: {len(new_venues)}")

    if not new_venues:
        print("All venues exist in DanceDB!")
        return

    print(f"\nMissing venues: {new_venues}")

    for venue_name in new_venues:
        print(f"\n--- Creating venue: {venue_name} ---")

        gmaps = f'https://www.google.com/maps/search/{venue_name.replace(" ", "+")}'
        osm = f'https://www.openstreetmap.org/search?query={venue_name.replace(" ", "%20")}'
        print(f"Google: {gmaps}")
        print(f"OSM: {osm}")

        coords = None
        print("Enter coordinates (lat, lng) or press Enter to skip:")
        coords_input = input("> ").strip()
        if coords_input:
            try:
                lat, lng = map(float, coords_input.split(","))
                coords = {"lat": lat, "lng": lng}
            except:
                print("Invalid format, skipping")

        if not coords:
            print("Skipping venue creation (no coordinates)")
            continue

        if dry_run:
            print(f"[DRY RUN] Would create: {venue_name} at {coords}")
            continue

        qid = create_venue(venue_name, coords["lat"], coords["lng"])
        if qid:
            print(f"Created: https://dance.wikibase.cloud/wiki/Item:{qid}")
            existing_venues[venue_name.lower()] = {"qid": qid, "lat": coords["lat"], "lng": coords["lng"]}
        else:
            print("Failed to create venue")

    print("\nVenue matching done. Run 'cli.py upload-events' to process events.")