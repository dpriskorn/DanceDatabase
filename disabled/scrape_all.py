import logging
import os
import datetime
from pathlib import Path

import config
from src.models.scrapers.dansgladje import Dansgladje

logging.basicConfig(level=config.loglevel)

# Create output folder with today's date
today = datetime.date.today().strftime("%Y%m%d")
output_folder = Path("../data") / today
os.makedirs(output_folder, exist_ok=True)

# run scrapers sequentially
d = Dansgladje(json_output_folder=output_folder)
d.start()
