"""Coordinate-based venue lookup utilities."""
import logging
import math

from src.utils.distance import haversine_distance

logger = logging.getLogger(__name__)


def find_dancedb_venues_by_coords(lat: float, lng: float, threshold_km: float = 0.1) -> list[dict]:
    """Query DanceDB for venues within distance threshold.

    Uses wikibase:box for bounding box query, then filters by exact haversine distance.
    Returns list of {qid, label, lat, lng, distance_km}.
    """
    from wikibaseintegrator.wbi_helpers import execute_sparql_query

    lat_delta = threshold_km / 111
    lng_delta = threshold_km / (111 * math.cos(math.radians(lat)))

    lng_min = lng - lng_delta
    lng_max = lng + lng_delta
    lat_min = lat - lat_delta
    lat_max = lat + lat_delta

    sparql = f"""
    PREFIX dd: <https://dance.wikibase.cloud/entity/>
    PREFIX ddt: <https://dance.wikibase.cloud/prop/direct/>
    PREFIX geo: <http://www.opengis.net/ont/geosparql#>
    PREFIX bd: <http://www.bigdata.com/rdf#>

    SELECT ?item ?itemLabel ?location WHERE {{
      SERVICE wikibase:box {{
        ?item ddt:P4 ?location .
        bd:serviceParam wikibase:cornerWest "Point({lng_min} {lat_min})"^^geo:wktLiteral .
        bd:serviceParam wikibase:cornerEast "Point({lng_max} {lat_max})"^^geo:wktLiteral .
      }}
      ?item ddt:P1 dd:Q20 .
      OPTIONAL {{ ?item rdfs:label ?itemLabel FILTER(LANG(?itemLabel) = "sv") }}
    }}
    """
    try:
        results = execute_sparql_query(query=sparql)
    except Exception as e:
        logger.warning(f"SPARQL error: {e}")
        return []

    matches = []
    for binding in results.get("results", {}).get("bindings", []):
        qid = binding.get("item", {}).get("value", "").rsplit("/", 1)[-1]
        label = binding.get("itemLabel", {}).get("value", "")
        geo_str = binding.get("location", {}).get("value", "")
        if not qid or not geo_str:
            continue
        try:
            coords = geo_str.replace("Point(", "").replace(")", "").split(" ")
            venue_lng, venue_lat = float(coords[0]), float(coords[1])
            dist = haversine_distance(lat, lng, venue_lat, venue_lng)
            if dist <= threshold_km:
                matches.append({
                    "qid": qid,
                    "label": label or qid,
                    "lat": venue_lat,
                    "lng": venue_lng,
                    "distance_km": dist,
                })
        except Exception as e:
            logger.warning(f"Parse error for {geo_str}: {e}")

    matches.sort(key=lambda x: x["distance_km"])
    return matches
