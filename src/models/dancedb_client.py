import logging
from typing import Optional

import questionary
from wikibaseintegrator import WikibaseIntegrator, datatypes
from wikibaseintegrator.wbi_login import Login
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator.wbi_helpers import execute_sparql_query

import config

logger = logging.getLogger(__name__)

wbi_config['MEDIAWIKI_API_URL'] = 'https://dance.wikibase.cloud/w/api.php'
wbi_config['SPARQL_ENDPOINT_URL'] = 'https://dance.wikibase.cloud/query/sparql'
wbi_config['WIKIBASE_URL'] = 'https://dance.wikibase.cloud'


class DancedbClient:
    def __init__(self):
        self.login = Login(user=config.username, password=config.password)
        self.wbi = WikibaseIntegrator(login=self.login)
        self.base_url = wbi_config['WIKIBASE_URL']

    def search_band(self, band_name: str) -> Optional[str]:
        sparql = f"""
        SELECT ?item WHERE {{
          ?item rdfs:label "{band_name}"@sv .
          {{ ?item wdt:P31 wd:Q215380 }} UNION
          {{ ?item wdt:P31 wd:Q2088357 }} UNION
          {{ ?item wdt:P31 wd:Q486161 }}
          FILTER NOT EXISTS {{ ?item wdt:P576 ?dissolutionDate }}
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

    def create_band(self, band_name: str) -> str:
        if not questionary.confirm(f"Create new band '{band_name}' on DanceDB?", default=True).ask():
            raise Exception(f"User declined to create band: {band_name}")

        try:
            new_item = self.wbi.item.new()
            new_item.labels.set('sv', band_name)
            new_item.labels.set('en', band_name)
            new_item.claims.add(datatypes.Item(prop_nr='P31', value='Q215380'))
            new_item.write(login=self.wbi.login)
            qid = new_item.id
            url = f"{self.base_url}/wiki/Item:{qid}"
            logger.info(f"Created band '{band_name}' on DanceDB: %s", url)
            return qid
        except Exception as e:
            logger.error(f"Error creating band '{band_name}': %s", e)
            raise

    def get_or_create_band(self, band_name: str) -> Optional[str]:
        qid = self.search_band(band_name)
        if qid:
            return qid
        return self.create_band(band_name)

    def create_venue(
        self,
        venue_name: str,
        ort: str = "",
        lat: float | None = None,
        lng: float | None = None,
        external_ids: dict[str, str] | None = None,
    ) -> str:
        """Create venue item in DanceDB.

        Uses wikibaseintegrator to create item with:
        - Labels: sv (venue_name + ', ' + ort if provided)
        - P1: instance of Q20 (dansställe)
        - P4: coordinates (if lat/lng provided)
        - External IDs (dict of prop_nr -> value, e.g. {"P44": "folkets-id"})

        Returns the new QID.
        """
        label = f"{venue_name}, {ort}" if ort else venue_name

        new_item = self.wbi.item.new()
        new_item.labels.set('sv', label)
        new_item.descriptions.set('sv', 'dansställe')

        if "Folkets" in venue_name:
            if "Folkets Park" in venue_name:
                place = venue_name.replace("Folkets Park", "").strip()
                alias = f"{place} Folkets Park"
            elif "Folkets Hus" in venue_name:
                place = venue_name.replace("Folkets Hus", "").strip()
                alias = f"{place} Folkets Hus"
            else:
                alias = None
            if alias:
                new_item.aliases.set("sv", alias)

        new_item.claims.add(datatypes.Item(prop_nr='P1', value='Q20'))

        if lat is not None and lng is not None:
            new_item.claims.add(
                datatypes.GlobeCoordinate(
                    prop_nr='P4',
                    latitude=lat,
                    longitude=lng,
                    precision=0.0001,
                    globe='http://www.wikidata.org/entity/Q2'
                )
            )

        if external_ids:
            for prop_nr, value in external_ids.items():
                new_item.claims.add(datatypes.ExternalID(prop_nr=prop_nr, value=value))

        new_item.write(login=self.wbi.login)
        qid = new_item.id
        url = f"{self.base_url}/wiki/Item:{qid}"
        logger.info(f"Created venue '{label}' on DanceDB: %s", url)
        return qid

    def create_venue_from_mapping(
        self,
        venue_name: str,
        ort: str = "",
        lat: float | None = None,
        lng: float | None = None,
    ) -> Optional[str]:
        """Create venue in DanceDB with optional coordinates.

        Handles creation errors gracefully. Returns QID on success, None on failure.
        """
        try:
            return self.create_venue(venue_name, ort, lat, lng)
        except Exception as e:
            logger.error(f"Error creating venue '{venue_name}': {e}")
            return None

    def create_event(
        self,
        label_sv: str,
        venue_qid: str,
        start_timestamp: datetime | None = None,
        end_timestamp: datetime | None = None,
        status_qid: str = "Q566",
    ) -> str:
        """Create event item in DanceDB.

        Uses wikibaseintegrator to create item with:
        - Labels: sv (label_sv)
        - P1: Q2 (instance of event)
        - P5: start timestamp (if provided)
        - P6: end timestamp (if provided)
        - P7: venue reference
        - P43: status (planned/cancelled)

        Returns the new QID.
        """
        from datetime import datetime, timezone

        new_item = self.wbi.item.new()
        new_item.labels.set('sv', label_sv)

        new_item.claims.add(datatypes.Item(prop_nr='P1', value='Q2'))
        new_item.claims.add(datatypes.Item(prop_nr='P7', value=venue_qid))

        if start_timestamp:
            start_time = start_timestamp.astimezone(timezone.utc).strftime('+%Y-%m-%dT00:00:00Z')
            new_item.claims.add(
                datatypes.Time(
                    prop_nr='P5',
                    time=start_time,
                    calendarmodel='http://www.wikidata.org/wiki/Special:Entity/Q1985787',
                    precision=11,
                )
            )

        if end_timestamp:
            end_time = end_timestamp.astimezone(timezone.utc).strftime('+%Y-%m-%dT00:00:00Z')
            new_item.claims.add(
                datatypes.Time(
                    prop_nr='P6',
                    time=end_time,
                    calendarmodel='http://www.wikidata.org/wiki/Special:Entity/Q1985787',
                    precision=11,
                )
            )

        new_item.write(login=self.wbi.login)
        qid = new_item.id
        url = f"{self.base_url}/wiki/Item:{qid}"
        logger.info(f"Created event '{label_sv}' on DanceDB: %s", url)
        return qid
