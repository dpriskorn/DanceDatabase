import logging
import os
import datetime
import time
import subprocess
from pathlib import Path

import config
import validate_data

logging.basicConfig(level=config.loglevel)
logger = logging.getLogger(__name__)

# Create output folder with today's date
today = datetime.date.today().strftime("%Y%m%d")
output_folder = Path("data") / today
os.makedirs(output_folder, exist_ok=True)


logger.info("Scraping started...")

start_total = time.time()

# Run onbeat scraper
start = time.time()
subprocess.run(["python", "scrape_onbeat.py"], check=True)
logger.info(f"Onbeat finished in {time.time() - start:.2f} seconds")

# Run danslogen scraper
start = time.time()
subprocess.run(["python", "scrape_danslogen.py"], check=True)
logger.info(f"Danslogen finished in {time.time() - start:.2f} seconds")

# Run cogwork scrapers
start = time.time()
subprocess.run(["python", "scrape_cogwork.py"], check=True)
logger.info(f"Cogwork finished in {time.time() - start:.2f} seconds")


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
