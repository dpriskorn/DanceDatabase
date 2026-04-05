import logging
import os
import datetime
import time
import subprocess
from pathlib import Path

from src.models.scrapers.altira import Altira
from src.models.scrapers.dansgladje import Dansgladje
from src.models.scrapers.bdk import Bdk

import config
from src.models.scrapers.fox4u import Fox4u
from src.models.scrapers.forsfox import Forsfox
from src.models.scrapers.foxunlimited import Foxunlimited
from src.models.scrapers.fmsab import Fmsab
from src.models.scrapers.gasasteget import Gasasteget
from src.models.scrapers.nimbusdk import Nimbusdk
from src.models.scrapers.wannadance import Wannadance
import validate_data

logging.basicConfig(level=config.loglevel)
logger = logging.getLogger(__name__)

# Create output folder with today's date
today = datetime.date.today().strftime("%Y%m%d")
output_folder = Path("data") / today
os.makedirs(output_folder, exist_ok=True)


logger.info("Scraping started...")

start_total = time.time()

start = time.time()
d = Dansgladje(json_output_folder=output_folder)
d.start()
logger.info(f"Dansgladje finished in {time.time() - start:.2f} seconds")

start = time.time()
bdk = Bdk(json_output_folder=output_folder)
bdk.start()
logger.info(f"Bdk finished in {time.time() - start:.2f} seconds")

start = time.time()
altira = Altira(json_output_folder=output_folder)
altira.start()
logger.info(f"Altira finished in {time.time() - start:.2f} seconds")

start = time.time()
ff = Forsfox(json_output_folder=output_folder)
ff.start()
logger.info(f"Forsfox finished in {time.time() - start:.2f} seconds")

start = time.time()
fu = Foxunlimited(json_output_folder=output_folder)
fu.start()
logger.info(f"Foxunlimited finished in {time.time() - start:.2f} seconds")

start = time.time()
fmsab = Fmsab(json_output_folder=output_folder)
fmsab.start()
logger.info(f"Fmsab finished in {time.time() - start:.2f} seconds")

start = time.time()
f4u = Fox4u(json_output_folder=output_folder)
f4u.start()
logger.info(f"Fox4u finished in {time.time() - start:.2f} seconds")

start = time.time()
wan = Wannadance(json_output_folder=output_folder)
wan.start()
logger.info(f"Wannadance finished in {time.time() - start:.2f} seconds")

start = time.time()
nim = Nimbusdk(json_output_folder=output_folder)
nim.start()
logger.info(f"Nimbusdk finished in {time.time() - start:.2f} seconds")

start = time.time()
gas = Gasasteget(json_output_folder=output_folder)
gas.start()
logger.info(f"Gasasteget finished in {time.time() - start:.2f} seconds")

# Run onbeat scraper
start = time.time()
subprocess.run(["python", "scrape_onbeat.py"], check=True)
logger.info(f"Onbeat finished in {time.time() - start:.2f} seconds")


logger.info(f"All scrapers finished in {time.time() - start_total:.2f} seconds")


# Validate all scraped JSON files against schema
print("\n=== Validating JSON files ===")
schema = validate_data.load_schema()
json_files = list(output_folder.glob("*.json"))

for file_path in sorted(json_files):
    is_valid, msg = validate_data.validate_file(file_path, schema)
    if is_valid:
        print(f"[OK] {file_path.name}: {msg}")
    else:
        print(f"[FAIL] {file_path.name}: {msg}")
