import os
import datetime
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from importlib import import_module
import pkgutil

# Folder where spiders are located
SPIDERS_PACKAGE = "models.spiders"

# Create output folder with today's date
today = datetime.date.today().strftime("%Y%m%d")
output_folder = os.path.join("data", today)
os.makedirs(output_folder, exist_ok=True)

# Get Scrapy settings
settings = get_project_settings()
settings.set("FEED_FORMAT", "json")      # output format
settings.set("FEED_EXPORT_ENCODING", "utf-8")  # UTF-8 encoding
# FEED_URI will be set per spider

# Dynamically import all spiders from models/spiders/
spiders_module = import_module(SPIDERS_PACKAGE)
spider_names = [
    name for _, name, _ in pkgutil.iter_modules(spiders_module.__path__)
]

process = CrawlerProcess(settings)

for spider_name in spider_names:
    # Construct spider class (assumes class name matches filename in CamelCase)
    module = import_module(f"{SPIDERS_PACKAGE}.{spider_name}")
    class_name = "".join(x.capitalize() for x in spider_name.split("_"))
    spider_class = getattr(module, class_name)

    # Set output file per spider
    output_file = os.path.join(output_folder, f"{spider_name}.json")
    settings.set("FEED_URI", output_file)

    # Schedule the spider
    process.crawl(spider_class)

# Start crawling
process.start()
