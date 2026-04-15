import json
import logging
import math
import urllib.parse
from datetime import date
from pathlib import Path

import questionary
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel

import config
from src.models.dancedb.client import DancedbClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=config.loglevel)

API_URL = "https://www.folketshusochparker.se/wp-content/themes/fhp/inc/ajax.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:149.0) Gecko/20100101 Firefox/149.0",
    "Accept": "*/*",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.folketshusochparker.se/medlemmar/",
}

FUZZY_THRESHOLD = 85
COORD_DISTANCE_KM = 1.0

UNMATCHED_DIR = Path("data") / "folketshus" / "unmatched"
ENRICHED_DIR = Path("data") / "folketshus" / "enriched"


class FolketshusVenue(BaseModel):
    name: str
    url: str
    lat: float
    lng: float
    region: str
    external_id: str = ""


def extract_external_id(url: str) -> str:
    """Extract folketshus ID from URL path.

    https://www.folketshusochparker.se/arrangor/sundsvalls-folkets-hus-och-park/
    → sundsvalls-folkets-hus-och-park
    """
    if not url:
        return ""
    try:
        path = urllib.parse.urlparse(url).path
        parts = path.rstrip("/").split("/")
        return parts[-1] if parts else ""
    except Exception:
        return ""


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two points in km."""
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def fuzzy_match(text: str, candidates: dict[str, str]) -> tuple[str, str, float] | None:
    """Fuzzy match text against candidates. Returns (label, qid, score) or None."""
    from rapidfuzz import fuzz

    text_lower = text.lower()
    best = None
    best_score = 0
    for label_lower, qid in candidates.items():
        score = fuzz.ratio(text_lower, label_lower)
        if score >= FUZZY_THRESHOLD and score > best_score:
            best_score = score
            best = (label_lower, qid)
    if best_score >= FUZZY_THRESHOLD:
        return (best[0], best[1], best_score)
    return None


def fetch_members() -> list[FolketshusVenue]:
    response = requests.post(
        API_URL,
        data={"action": "get_members", "type": "member", "search": ""},
        headers=HEADERS,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("success"):
        raise ValueError(f"API returned success=false: {data}")
    html_fragments = data.get("data", {}).get("results", [])
    venues = []
    for html in html_fragments:
        venue = parse_venue(html)
        if venue:
            venues.append(venue)
    logger.info(f"Parsed {len(venues)} venues from {len(html_fragments)} HTML fragments")
    return venues


def parse_venue(html: str) -> FolketshusVenue | None:
    soup = BeautifulSoup(html, "lxml")
    article = soup.find("article")
    if not article:
        return None
    lat = article.get("data-lat")
    lng = article.get("data-lng")
    if not lat or not lng:
        logger.warning("Missing coordinates in article")
        return None
    link = article.find("a", class_="card-body--link")
    if not link:
        return None
    title_attr = link.get("title", "")
    h3_tag = link.find("h3", class_="card-title")
    name = title_attr or (h3_tag.get_text(strip=True) if h3_tag else "")
    if not name:
        logger.warning("Missing venue name")
        logger.debug(f"Malformed HTML fragment (len={len(html)}): {html[:500]}")
        return None
    url = link.get("href", "")
    external_id = extract_external_id(url)
    region_div = link.find("div", class_="card-content")
    region = region_div.get_text(strip=True) if region_div else ""
    return FolketshusVenue(name=name, url=url, lat=float(lat), lng=float(lng), region=region, external_id=external_id)


def fetch_existing_venues() -> dict[str, dict]:
    """Fetch existing venues from DanceDB via SPARQL."""
    from wikibaseintegrator.wbi_config import config as wbi_config
    from wikibaseintegrator.wbi_helpers import execute_sparql_query

    wbi_config["USER_AGENT"] = config.user_agent

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

    logger.info(f"Fetched {len(venues)} existing venues from DanceDB")
    return venues


def match_venues(venues: list[FolketshusVenue]) -> tuple[list[dict], list[FolketshusVenue]]:
    """Match folketshus venues to DanceDB venues."""
    print("\n=== Matching venues to DanceDB ===")

    db_venues = fetch_existing_venues()
    db_labels = {v["label"].lower(): qid for qid, v in db_venues.items()}
    db_coords = {qid: (v["lat"], v["lng"]) for qid, v in db_venues.items() if v["lat"] and v["lng"]}

    enriched = []
    unmatched = []

    for venue in venues:
        name_lower = venue.name.lower()
        matched_qid = None

        if name_lower in db_labels:
            matched_qid = db_labels[name_lower]
            print(f"Exact match: {venue.name} -> {matched_qid}")
        else:
            fuzzy = fuzzy_match(venue.name, db_labels)
            if fuzzy:
                matched_qid = fuzzy[1]
                print(f"Fuzzy match: {venue.name} -> {matched_qid} ('{fuzzy[0]}', score={fuzzy[2]})")
            else:
                for qid, (lat2, lng2) in db_coords.items():
                    dist = haversine_distance(venue.lat, venue.lng, lat2, lng2)
                    if dist <= COORD_DISTANCE_KM:
                        matched_qid = qid
                        print(f"Coord match: {venue.name} -> {qid} ({dist:.1f}km)")
                        break

        if matched_qid:
            enriched.append(
                {
                    "name": venue.name,
                    "url": venue.url,
                    "lat": venue.lat,
                    "lng": venue.lng,
                    "region": venue.region,
                    "external_id": venue.external_id,
                    "qid": matched_qid,
                }
            )
        else:
            unmatched.append(venue)

    return enriched, unmatched


def create_venue_with_p44(venue: FolketshusVenue) -> str | None:
    """Create venue in DanceDB with P44 external ID."""
    from wikibaseintegrator import datatypes
    from wikibaseintegrator.bwitems import Item

    external_id = venue.external_id or extract_external_id(venue.url)
    label = venue.name

    new_item = Item.new()
    new_item.labels.set("sv", label)
    new_item.descriptions.set("sv", "dansställe")

    new_item.claims.add(datatypes.Item(prop_nr="P1", value="Q20"))
    new_item.claims.add(
        datatypes.GlobeCoordinate(prop_nr="P4", latitude=venue.lat, longitude=venue.lng, precision=0.0001, globe="http://www.wikidata.org/entity/Q2")
    )
    if external_id:
        new_item.claims.add(datatypes.ExternalID(prop_nr="P44", value=external_id))

    try:
        new_item.write(login=DancedbClient().wbi.login)
        qid = new_item.id
        logger.info(f"Created venue '{label}' with P44={external_id}: {qid}")
        return qid
    except Exception as e:
        logger.error(f"Error creating venue '{label}': {e}")
        return None


def run(date_str: str | None = None, match: bool = False) -> None:
    logger.info("Fetching folketshus och parker venues...")
    venues = fetch_members()
    print(f"Found {len(venues)} venues.")

    date_val = date_str or date.today().strftime("%Y-%m-%d")
    UNMATCHED_DIR.mkdir(parents=True, exist_ok=True)
    ENRICHED_DIR.mkdir(parents=True, exist_ok=True)

    if match:
        enriched, unmatched = match_venues(venues)

        enriched_file = ENRICHED_DIR / f"{date_val}.json"
        enriched_file.write_text(json.dumps(enriched, indent=2, ensure_ascii=False) + "\n")
        print(f"Saved enriched to {enriched_file}")

        unmatched_file = UNMATCHED_DIR / f"{date_val}.json"
        unmatched_file.write_text(json.dumps([v.model_dump() for v in unmatched], indent=2, ensure_ascii=False) + "\n")
        print(f"Saved unmatched to {unmatched_file}")

        print(f"\nMatched: {len(enriched)}")
        print(f"Unmatched: {len(unmatched)}")

        if unmatched:
            print("\n=== Creating unmatched venues in DanceDB ===")
            create = questionary.confirm("Create unmatched venues in DanceDB?").ask()
            if create:
                for venue in unmatched:
                    print(f"\nCreating: {venue.name}")
                    qid = create_venue_with_p44(venue)
                    if qid:
                        print(f"  Created: {qid}")
    else:
        output_file = UNMATCHED_DIR / f"{date_val}.json"
        output_file.write_text(json.dumps([v.model_dump() for v in venues], indent=2, ensure_ascii=False) + "\n")
        print(f"Saved to {output_file}")
