from wikibaseintegrator.wbi_config import config
import logging

# ---- Setup logging ----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---- Configure your Wikibase instance ----
config['MEDIAWIKI_API_URL'] = 'https://dance.wikibase.cloud/w/api.php'
config['SPARQL_ENDPOINT_URL'] = 'https://dance.wikibase.cloud/query/sparql'
config['WIKIBASE_URL'] = 'https://dance.wikibase.cloud'

# ---- Authentication ----
# Uncomment and set if you want to write changes
# config['USER_LOGIN'] = 'your_username'
# config['USER_PASSWORD'] = 'your_password'

# ---- SPARQL query to find Swedish label clashes ----
sparql_query = """
PREFIX dd: <https://dance.wikibase.cloud/entity/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?qid ?itemLabel WHERE {
  ?item rdfs:label ?itemLabel .
  FILTER(LANG(?itemLabel) = "sv") .

  # Find other items with the same label
  ?otherItem rdfs:label ?itemLabel .
  FILTER(LANG(?itemLabel) = "sv") .
  FILTER(?otherItem != ?item)

  # Extract QID from URL
  BIND(STRAFTER(STR(?item), "/entity/") AS ?qid)
}
GROUP BY ?qid ?itemLabel
ORDER BY ?itemLabel
"""

# ---- Run SPARQL query ----
sparql = execute_sparql_query(endpoint_url=config['SPARQL_ENDPOINT_URL'])
results = sparql.query(sparql_query)

# ---- Process each clashing item ----
for result in results['results']['bindings']:
    qid = result['qid']['value']
    label = result['itemLabel']['value']
    logger.info(f"Clashing item: {qid} ({label})")

    try:
        item = Item(item_id=qid)

        # Optional: fetch current description
        current_desc = item.get_description('sv')
        logger.info(f"{qid}: current sv description: {current_desc}")

        # Example: set a temporary description to flag clash
        new_desc = "OBS: klonad etikett, behöver disambiguering"
        item.set_description(new_desc, lang='sv')

        # Write changes to Wikibase (uncomment to apply)
        # item.write(login=config['USER_LOGIN'], password=config['USER_PASSWORD'])
        logger.info(f"{qid}: description updated to: {new_desc}")

    except Exception as e:
        logger.error(f"Error processing {qid}: {e}")
