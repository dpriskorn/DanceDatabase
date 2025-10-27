import logging
import os
import datetime
import json
import time
from pathlib import Path
from pydantic import ValidationError  # ✅ correct import (not from _pydantic_core)

from src.models.onbeat.organizers import OnbeatOrganizers
from src.models.scrapers.altira import Altira
from src.models.scrapers.dansgladje import Dansgladje
from src.models.scrapers.bdk import Bdk
from src.models.dance_event import DanceEvent

import config
from src.models.scrapers.fox4u import Fox4u
from src.models.scrapers.forsfox import Forsfox
from src.models.scrapers.foxunlimited import Foxunlimited
from src.models.scrapers.gasasteget import Gasasteget
from src.models.scrapers.nimbusdk import Nimbusdk
from src.models.scrapers.wannadance import Wannadance

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

start = time.time()
onb = OnbeatOrganizers(json_output_folder=output_folder)
onb.start()
logger.info(f"Gasasteget finished in {time.time() - start:.2f} seconds")


logger.info(f"All scrapers finished in {time.time() - start_total:.2f} seconds")


# ✅ include subfolders recursively and match json files correctly
json_files = list(output_folder.rglob("*.json"))

for file_path in json_files:
    print(f"Validating {file_path}...")
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # ✅ handle either a list or a single event object
        if isinstance(data, list):
            for i, item in enumerate(data, start=1):
                try:
                    DanceEvent(**item)
                except ValidationError as e:
                    print(f"❌ {file_path} (item #{i}) is invalid!")
                    print(e)
                    break
            else:
                print(f"✅ {file_path} (list of {len(data)}) is valid.")
        else:
            DanceEvent(**data)
            print(f"✅ {file_path} is valid.")

    except (ValidationError, json.JSONDecodeError) as e:
        print(f"❌ {file_path} is invalid!")
        print(e)
