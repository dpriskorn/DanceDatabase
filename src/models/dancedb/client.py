import logging
from typing import Optional

from datetime import datetime
import questionary
import rich
from wikibaseintegrator import WikibaseIntegrator, datatypes
from wikibaseintegrator.wbi_login import Login
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator.wbi_helpers import execute_sparql_query

import config

wbi_config['MEDIAWIKI_API_URL'] = 'https://dance.wikibase.cloud/w/api.php'
wbi_config['SPARQL_ENDPOINT_URL'] = 'https://dance.wikibase.cloud/query/sparql'
wbi_config['WIKIBASE_URL'] = 'https://dance.wikibase.cloud'
wbi_config['USER_AGENT'] = config.user_agent

logger = logging.getLogger(__name__)


class DancedbClient:
    def __init__(self):
        self.login = Login(user=config.username, password=config.password)
        self.wbi = WikibaseIntegrator(login=self.login)
        self.base_url = wbi_config['WIKIBASE_URL']

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
            items = results['results']['bindings']
            if len(items) == 1:
                qid = items[0]['item']['value'].rsplit('/', 1)[-1]
                logger.info(f"Found band '{band_name}' on DanceDB: {self.base_url}/wiki/Item:{qid}")
                return qid
            elif len(items) > 1:
                logger.warning(f"Multiple matches for '{band_name}': {[i['item']['value'] for i in items]}")
            return None
        except Exception as e:
            logger.error(f"Error searching for '{band_name}': {e}")
            return None

    def create_band(self, band_name: str, spelplan_id: str = "") -> str:
        if not questionary.confirm(f"Create new band '{band_name}' on DanceDB?", default=True).ask():
            raise Exception(f"User declined to create band: {band_name}")

        try:
            new_item = self.wbi.item.new()
            new_item.labels.set('sv', band_name)
            new_item.labels.set('en', band_name)
            new_item.descriptions.set('sv', 'artist')
            new_item.claims.add(datatypes.Item(prop_nr='P1', value='Q225'))
            if spelplan_id:
                spelplan_url = f"https://danslogen.se/spelplan/{spelplan_id}"
                new_item.claims.add(datatypes.Item(prop_nr='P46', value=spelplan_url))
                logger.info(f"Band '{band_name}' spelplan: %s", spelplan_url)
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

        Returns list of {qid, label, aliases, p3}.
        """
        sparql = """
PREFIX dd: <https://dance.wikibase.cloud/entity/>
PREFIX ddt: <https://dance.wikibase.cloud/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?item ?label ?altLabel ?p3 WHERE {
    ?item ddt:P1 dd:Q225 .
    OPTIONAL { ?item rdfs:label ?label FILTER(LANG(?label) = "sv") }
    OPTIONAL { ?item skos:altLabel ?altLabel FILTER(LANG(?altLabel) = "sv") }
    OPTIONAL { ?item ddt:P3 ?p3 }
}
"""
        try:
            results = execute_sparql_query(sparql)
            items = []
            for row in results.get('results', {}).get('bindings', []):
                qid = row['item']['value'].rsplit('/', 1)[-1]
                label = row.get('label', {}).get('value', '')
                alt_labels = row.get('altLabel', {}).get('value', '').split(',') if 'altLabel' in row else []
                p3 = row.get('p3', {}).get('value', '')
                items.append({'qid': qid, 'label': label, 'aliases': alt_labels, 'p3': p3})
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
            for row in results.get('results', {}).get('bindings', []):
                qid = row['item']['value'].rsplit('/', 1)[-1]
                label = row.get('label', {}).get('value', '')
                alt_labels = row.get('altLabel', {}).get('value', '').split(',') if 'altLabel' in row else []
                p4 = row.get('p4', {}).get('value', '')
                venues.append({'qid': qid, 'label': label, 'aliases': alt_labels, 'p4': p4})
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
            items = results['results']['bindings']
            if len(items) == 1:
                qid = items[0]['item']['value'].rsplit('/', 1)[-1]
                logger.info(f"Found venue '{venue_name}' on DanceDB: {self.base_url}/wiki/Item:{qid}")
                return qid
            elif len(items) > 1:
                logger.warning(f"Multiple matches for '{venue_name}': {[i['item']['value'] for i in items]}")
            return None
        except Exception as e:
            logger.error(f"Error searching for '{venue_name}': {e}")
            return None

    def create_venue(self, venue_name: str, latitude: float = 0.0, longitude: float = 0.0) -> str:
        """Create a new venue on DanceDB with optional coordinates."""
        if not questionary.confirm(f"Create new venue '{venue_name}' on DanceDB?", default=True).ask():
            raise Exception(f"User declined to create venue: {venue_name}")

        try:
            new_item = self.wbi.item.new()
            new_item.labels.set('sv', venue_name)
            new_item.labels.set('en', venue_name)
            new_item.claims.add(datatypes.Item(prop_nr='P1', value='Q20'))
            if latitude and longitude:
                new_item.claims.add(datatypes.GlobeCoordinate(
                    prop_nr='P4',
                    latitude=latitude,
                    longitude=longitude,
                    precision=0.0001,
                    globe='http://www.wikidata.org/entity/Q2'
                ))
            new_item.write(login=self.wbi.login)
            qid = new_item.id
            url = f"{self.base_url}/wiki/Item:{qid}"
            logger.info(f"Created venue '{venue_name}' on DanceDB: %s", url)
            rich.print(f"[green]Created venue: {url}[/green]")
            return qid
        except Exception as e:
            logger.error(f"Error creating venue '{venue_name}': {e}")
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

    def add_event(self, band_qid: str, venue_qid: str, start: datetime, end: datetime, status_qid: str = 'Q566') -> bool:
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
            event.labels.set('sv', f"Event {start.isoformat()}")
            event.labels.set('en', f"Event {start.isoformat()}")
            event.claims.add(datatypes.Item(prop_nr='P1', value='Q2'))
            event.claims.add(datatypes.Item(prop_nr='P7', value=venue_qid))
            event.claims.add(datatypes.Time(prop_nr='P5', time=start.strftime('+%Y-%m-%dT%H:%M:%S00'), precision=11))
            event.claims.add(datatypes.Time(prop_nr='P6', time=end.strftime('+%Y-%m-%dT%H:%M:%S00'), precision=11))
            event.claims.add(datatypes.Item(prop_nr='P43', value=status_qid))
            item_qid = event.write(login=self.wbi.login)
            logger.info(f"Created event {item_qid} for band {band_qid} at venue {venue_qid}")
            return True
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return False