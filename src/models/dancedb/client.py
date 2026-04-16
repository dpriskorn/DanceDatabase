import logging
import math
import sys
from datetime import datetime
from typing import Optional

import questionary
import rich
from wikibaseintegrator import WikibaseIntegrator, datatypes
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator.wbi_helpers import execute_sparql_query
from wikibaseintegrator.wbi_login import Login

import config

wbi_config["MEDIAWIKI_API_URL"] = "https://dance.wikibase.cloud/w/api.php"
wbi_config["SPARQL_ENDPOINT_URL"] = "https://dance.wikibase.cloud/query/sparql"
wbi_config["WIKIBASE_URL"] = "https://dance.wikibase.cloud"
wbi_config["USER_AGENT"] = config.user_agent

logger = logging.getLogger(__name__)


class DancedbClient:
    def __init__(self):
        self.login = Login(user=config.username, password=config.password)
        self.wbi = WikibaseIntegrator(login=self.login)
        self.base_url = wbi_config["WIKIBASE_URL"]

    def search_band(self, band_name: str) -> Optional[str]:
        sparql = f"""
        PREFIX dd: <https://dance.wikibase.cloud/entity/>
        PREFIX ddt: <https://dance.wikibase.cloud/prop/direct/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?item WHERE {{
          ?item rdfs:label "{band_name}"@sv .
          {{ ?item ddt:P1 dd:Q225 }}
        }}
        """
        try:
            results = execute_sparql_query(query=sparql)
            items = results["results"]["bindings"]
            if len(items) == 1:
                qid = items[0]["item"]["value"].rsplit("/", 1)[-1]
                logger.info(f"Found band '{band_name}' on DanceDB: {self.base_url}/wiki/Item:{qid}")
                return qid
            elif len(items) > 1:
                logger.warning(f"Multiple matches for '{band_name}': {[i['item']['value'] for i in items]}")
            return None
        except Exception as e:
            logger.error(f"Error searching for '{band_name}': {e}")
            return None

    def create_band(self, band_name: str, spelplan_id: str = "") -> str:
        confirm = questionary.select(
            f"Create new band '{band_name}' on DanceDB?", choices=["Yes (Recommended)", "No", "Abort"]
        ).ask()
        if confirm == "No":
            raise Exception(f"User declined to create band: {band_name}")
        elif confirm == "Abort":
            print("Aborting...")
            sys.exit(0)

        try:
            new_item = self.wbi.item.new()
            new_item.labels.set("sv", band_name)
            new_item.labels.set("en", band_name)
            new_item.descriptions.set("sv", "artist")
            new_item.claims.add(datatypes.Item(prop_nr="P1", value="Q225"))
            if spelplan_id:
                new_item.claims.add(datatypes.String(prop_nr="P46", value=spelplan_id))
                logger.info(f"Band '{band_name}' P46: %s", spelplan_id)
            else:
                logger.warning(f"Band '{band_name}' created WITHOUT spelplan_id (P46)")
            new_item.write(login=self.wbi.login)
            qid = new_item.id
            url = f"{self.base_url}/wiki/Item:{qid}"
            logger.info(f"Created band '{band_name}' on DanceDB: %s", url)
            return qid
        except Exception as e:
            logger.error(f"Error creating band '{band_name}': {e}")
            raise

    def get_or_create_band(self, band_name: str, spelplan_id: str = "") -> Optional[str]:
        qid = self.search_band(band_name)
        if qid:
            return qid
        return self.create_band(band_name, spelplan_id)

    def fetch_artists_from_dancedb(self) -> list[dict]:
        """Fetch all artist items from DanceDB (instance of Q225).

        Returns list of {qid, label, aliases, p3, p46}.
        """
        sparql = """
PREFIX dd: <https://dance.wikibase.cloud/entity/>
PREFIX ddt: <https://dance.wikibase.cloud/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?item ?label ?altLabel ?p3 ?p46 WHERE {
    ?item ddt:P1 dd:Q225 .
    OPTIONAL { ?item rdfs:label ?label FILTER(LANG(?label) = "sv") }
    OPTIONAL { ?item skos:altLabel ?altLabel FILTER(LANG(?altLabel) = "sv") }
    OPTIONAL { ?item ddt:P3 ?p3 }
    OPTIONAL { ?item ddt:P46 ?p46 }
}
"""
        try:
            results = execute_sparql_query(sparql)
            items_dict = {}
            for row in results.get("results", {}).get("bindings", []):
                qid = row["item"]["value"].rsplit("/", 1)[-1]
                label = row.get("label", {}).get("value", "")
                alt_label = row.get("altLabel", {}).get("value", "")
                p3 = row.get("p3", {}).get("value", "")
                p46 = row.get("p46", {}).get("value", "")
                if qid not in items_dict:
                    items_dict[qid] = {"qid": qid, "label": label, "aliases": [], "p3": p3, "p46": p46}
                if alt_label:
                    items_dict[qid]["aliases"].append(alt_label.lower())
            items = list(items_dict.values())
            logger.info(f"Fetched {len(items)} artists from DanceDB")
            return items
        except Exception as e:
            logger.error(f"Error fetching artists: {e}")
            return []

    def fetch_venues_from_dancedb(self) -> list[dict]:
        """Fetch all venue items from DanceDB (instance of Q20).

        Returns list of {qid, label, aliases, p4 (coordinates)}.
        """
        sparql = """
PREFIX dd: <https://dance.wikibase.cloud/entity/>
PREFIX ddt: <https://dance.wikibase.cloud/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?item ?label ?altLabel ?p4 WHERE {
    ?item ddt:P1 dd:Q20 .
    OPTIONAL { ?item rdfs:label ?label FILTER(LANG(?label) = "sv") }
    OPTIONAL { ?item skos:altLabel ?altLabel FILTER(LANG(?altLabel) = "sv") }
    OPTIONAL { ?item ddt:P4 ?p4 }
}
"""
        try:
            results = execute_sparql_query(sparql)
            venues = []
            for row in results.get("results", {}).get("bindings", []):
                qid = row["item"]["value"].rsplit("/", 1)[-1]
                label = row.get("label", {}).get("value", "")
                alt_labels = row.get("altLabel", {}).get("value", "").split(",") if "altLabel" in row else []
                p4 = row.get("p4", {}).get("value", "")
                venues.append({"qid": qid, "label": label, "aliases": alt_labels, "p4": p4})
            logger.info(f"Fetched {len(venues)} venues from DanceDB")
            return venues
        except Exception as e:
            logger.error(f"Error fetching venues: {e}")
            return []

    def search_venue(self, venue_name: str) -> Optional[str]:
        """Search for venue by exact label match."""
        sparql = f"""
        PREFIX dd: <https://dance.wikibase.cloud/entity/>
        PREFIX ddt: <https://dance.wikibase.cloud/prop/direct/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

        SELECT ?item WHERE {{
          ?item rdfs:label "{venue_name}"@sv .
          ?item ddt:P1 dd:Q20 .
        }}
        """
        try:
            results = execute_sparql_query(query=sparql)
            items = results["results"]["bindings"]
            if len(items) == 1:
                qid = items[0]["item"]["value"].rsplit("/", 1)[-1]
                logger.info(f"Found venue '{venue_name}' on DanceDB: {self.base_url}/wiki/Item:{qid}")
                return qid
            elif len(items) > 1:
                logger.warning(f"Multiple matches for '{venue_name}': {[i['item']['value'] for i in items]}")
            return None
        except Exception as e:
            logger.error(f"Error searching for '{venue_name}': {e}")
            return None

    def find_venues_by_coordinates(self, lat: float, lng: float, threshold_km: float = 0.1) -> list[dict]:
        """Query DanceDB for venues within distance threshold.

        Uses wikibase:box for bounding box query, then filters by exact haversine distance.
        Returns list of {qid, label, lat, lng, distance_km}.
        """
        from src.utils.distance import haversine_distance

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
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

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

    def create_venue(self, venue_name: str, latitude: float = 0.0, longitude: float = 0.0, external_ids: dict[str, str] | None = None) -> str:
        """Create a new venue on DanceDB with optional coordinates."""
        confirm = questionary.select(
            f"Create new venue '{venue_name}' on DanceDB?", choices=["Yes (Recommended)", "No", "Abort"]
        ).ask()
        if confirm == "No":
            raise Exception(f"User declined to create venue: {venue_name}")
        elif confirm == "Abort":
            print("Aborting...")
            sys.exit(0)

        try:
            new_item = self.wbi.item.new()
            new_item.labels.set("sv", venue_name)
            new_item.labels.set("en", venue_name)
            new_item.descriptions.set("sv", "dansställe")
            new_item.claims.add(datatypes.Item(prop_nr="P1", value="Q20"))
            if latitude and longitude:
                new_item.claims.add(
                    datatypes.GlobeCoordinate(prop_nr="P4", latitude=latitude, longitude=longitude, precision=0.0001, globe="http://www.wikidata.org/entity/Q2")
                )
            if external_ids:
                for prop, value in external_ids.items():
                    new_item.claims.add(datatypes.String(prop_nr=prop, value=value))
            new_item.write(login=self.wbi.login)
            qid = new_item.id
            url = f"{self.base_url}/wiki/Item:{qid}"
            logger.info(f"Created venue '{venue_name}' on DanceDB: %s", url)
            rich.print(f"[green]Created venue: {url}[/green]")
            return qid
        except Exception as e:
            logger.error(f"Error creating venue '{venue_name}': %s", e)
            raise

    def get_or_create_venue(self, venue_name: str, latitude: float = 0.0, longitude: float = 0.0) -> str:
        """Get existing venue or create new one with optional coordinates."""
        qid = self.search_venue(venue_name)
        if qid:
            return qid
        return self.create_venue(venue_name, latitude, longitude)

    def set_property(self, qid: str, property_id: str, value: str) -> bool:
        """Set a property on an existing item. Returns True on success."""
        try:
            item = self.wbi.item.get(qid)
            item.claims.add(datatypes.Item(prop_nr=property_id, value=value))
            item.write(login=self.wbi.login)
            logger.info(f"Set {property_id}={value} on {qid}")
            return True
        except Exception as e:
            logger.error(f"Error setting property on '{qid}': {e}")
            return False

    def set_artist_spelplan(self, qid: str, spelplan_id: str) -> bool:
        """Set P46 (spelplan ID) on existing artist item. Returns True on success."""
        try:
            item = self.wbi.item.get(qid)
            item.claims.add(datatypes.String(prop_nr="P46", value=spelplan_id))
            item.write(login=self.wbi.login)
            logger.info(f"Added P46 to artist {qid}: {spelplan_id}")
            return True
        except Exception as e:
            logger.error(f"Error setting P46 on '{qid}': {e}")
            return False

    def add_event(self, band_qid: str, venue_qid: str, start: datetime, end: datetime, status_qid: str = "Q566") -> bool:
        """Add/创建一个新的活动事件.

        Args:
            band_qid: Band QID
            venue_qid: Venue QID
            start: Start datetime
            end: End datetime
            status_qid: Q566 (planned), Q567 (cancelled), etc.

        Returns True on success.
        """
        try:
            event = self.wbi.item.new()
            event.labels.set("sv", f"Event {start.isoformat()}")
            event.labels.set("en", f"Event {start.isoformat()}")
            event.claims.add(datatypes.Item(prop_nr="P1", value="Q2"))
            event.claims.add(datatypes.Item(prop_nr="P7", value=venue_qid))
            event.claims.add(datatypes.Time(prop_nr="P5", time=start.strftime("+%Y-%m-%dT%H:%M:%S00"), precision=11))
            event.claims.add(datatypes.Time(prop_nr="P6", time=end.strftime("+%Y-%m-%dT%H:%M:%S00"), precision=11))
            event.claims.add(datatypes.Item(prop_nr="P43", value=status_qid))
            item_qid = event.write(login=self.wbi.login)
            logger.info(f"Created event {item_qid} for band {band_qid} at venue {venue_qid}")
            return True
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return False

    def create_event(self, label_sv: str, venue_qid: str, start_timestamp: str, end_timestamp: str | None = None, status_qid: str = "Q566", instance_of: str = "Q2", artist_qid: str | None = None) -> str | None:
        """Create a new event on DanceDB.

        Args:
            label_sv: Event label in Swedish
            venue_qid: Venue QID
            start_timestamp: Start timestamp (ISO format)
            end_timestamp: End timestamp (ISO format)
            status_qid: Q566 (planned), Q567 (cancelled), etc.
            instance_of: Q2 (event)
            artist_qid: Artist QID (optional)

        Returns the created event QID or None on failure.
        """
        confirm = questionary.select(
            f"Create new event '{label_sv}' on DanceDB?", choices=["Yes (Recommended)", "No", "Abort"]
        ).ask()
        if confirm == "No":
            raise Exception(f"User declined to create event: {label_sv}")
        elif confirm == "Abort":
            print("Aborting...")
            sys.exit(0)

        try:
            event = self.wbi.item.new()
            event.labels.set("sv", label_sv)
            event.labels.set("en", label_sv)
            event.claims.add(datatypes.Item(prop_nr="P1", value=instance_of))
            event.claims.add(datatypes.Item(prop_nr="P7", value=venue_qid))
            
            # Format timestamps for Wikibase: +YYYY-MM-DDTHH:MM:00Z
            from datetime import datetime
            start_dt = datetime.fromisoformat(start_timestamp.replace("+01:00", "").replace("+02:00", ""))
            start_clean = f"+{start_dt.strftime('%Y-%m-%dT00:00:00Z')}"
            event.claims.add(datatypes.Time(prop_nr="P5", time=start_clean, precision="day"))
            if end_timestamp:
                end_dt = datetime.fromisoformat(end_timestamp.replace("+01:00", "").replace("+02:00", ""))
                end_clean = f"+{end_dt.strftime('%Y-%m-%dT00:00:00Z')}"
                event.claims.add(datatypes.Time(prop_nr="P6", time=end_clean, precision="day"))
            event.claims.add(datatypes.Item(prop_nr="P43", value=status_qid))
            if artist_qid:
                event.claims.add(datatypes.Item(prop_nr="P56", value=artist_qid))
            item_qid = event.write(login=self.wbi.login)
            url = f"{self.base_url}/wiki/Item:{item_qid}"
            logger.info(f"Created event '{label_sv}' on DanceDB: {url}")
            rich.print(f"[green]Created event: {url}[/green]")
            return item_qid
        except Exception as e:
            logger.error(f"Error creating event '{label_sv}': %s", e)
            raise
