import logging
from typing import Optional

import questionary
from wikibaseintegrator import wbi_helpers
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
            new_item = wbi_helpers.create_item(
                labels={'sv': band_name, 'en': band_name},
                login=self.login
            )
            qid = new_item.id
            new_item.claims.add('P31', 'Q215380')
            new_item.write(login=self.login)
            url = f"{self.base_url}/wiki/Item:{qid}"
            logger.info(f"Created band '{band_name}' on DanceDB: {url}")
            return qid
        except Exception as e:
            logger.error(f"Error creating band '{band_name}': {e}")
            raise

    def get_or_create_band(self, band_name: str) -> Optional[str]:
        qid = self.search_band(band_name)
        if qid:
            return qid
        return self.create_band(band_name)
