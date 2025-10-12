from collections import defaultdict

from wikibaseintegrator import wbi_helpers
from wikibaseintegrator.wbi_login import Login
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator.wbi_helpers import execute_sparql_query
import logging
import config

# ---- Setup logging ----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---- Configure your Wikibase instance ----
wbi_config['MEDIAWIKI_API_URL'] = 'https://dance.wikibase.cloud/w/api.php'
wbi_config['SPARQL_ENDPOINT_URL'] = 'https://dance.wikibase.cloud/query/sparql'
wbi_config['WIKIBASE_URL'] = 'https://dance.wikibase.cloud'

# ---- Login for write operations ----
login_instance = Login(user=config.username, password=config.password)

# ---- SPARQL query to find Swedish label clashes ----
sparql_query = """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?item ?itemLabel WHERE {
  ?item rdfs:label ?itemLabel .
  FILTER(LANG(?itemLabel) = "sv") .

  # Find other items with the same label
  ?otherItem rdfs:label ?itemLabel .
  FILTER(LANG(?itemLabel) = "sv") .
  FILTER(?otherItem != ?item)
}
ORDER BY ?itemLabel ?item
"""

# ---- Run SPARQL query ----
results = execute_sparql_query(endpoint_url=config['SPARQL_ENDPOINT_URL'])

# ---- Group clashing items by label ----
clashes = defaultdict(list)
for result in results['results']['bindings']:
    item_url = result['item']['value']
    qid = item_url.rsplit('/', 1)[-1]
    label = result['itemLabel']['value']
    clashes[label].append(qid)

# ---- Merge clashing items ----
for label, qids in clashes.items():
    if not qids:
        continue  # nothing to merge

    logger.info(f"Label '{label}' has clashing items: {qids}")
    response = input("Continue with merge? (y/n)")
    if response != "n":
        try:
            wbi_helpers.merge_items(
                qids=qids,
                login=login_instance,
                is_bot=True,
                ignore_conflicts=None
            )
            logger.info(f"Merged qids, see recent changes in the wikibase for an overview")

        except Exception as e:
            logger.error(f"Error merging {qids}: {e}")
