import logging
from pathlib import Path

import config
from src.models.danslogen import Danslogen

logging.basicConfig(level=config.loglevel)
logger = logging.getLogger(__name__)

output_folder = Path("data") / "danslogen"
output_folder.mkdir(parents=True, exist_ok=True)

scraper = Danslogen("april")
events = scraper.scrape_month("april")

output_file = output_folder / "danslogen-april.json"
import json
with open(output_file, "w") as f:
    json.dump([e.model_dump(mode="json") for e in events], f, ensure_ascii=False, indent=2)
logger.info(f"Wrote {len(events)} events to {output_file}")
