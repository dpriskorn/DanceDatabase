import json
import re
from typing import Any, Dict, List

import requests

from src.models.base import VenueSource


class BygdegardarnaSource(VenueSource):
    """Bygdegardarna venue source."""
    
    name = "bygdegardarna"

    def scrape_venues(self, **kwargs) -> list[dict[str, Any]]:
        """Scrape venues from bygdegardarna.se."""
        return scrape()

    def match_venues(self, venues: list[dict[str, Any]], **kwargs) -> list[dict[str, Any]]:
        """Match venues to DanceDB (implemented elsewhere)."""
        return venues


def scrape() -> List[Dict[str, Any]]:
    url = "https://bygdegardarna.se/hitta-bygdegard/"
    resp = requests.get(url)
    resp.raise_for_status()
    html = resp.text

    match = re.search(r"var markerData\s*=\s*(\[.*?\]);", html, re.DOTALL)
    if not match:
        raise ValueError("Could not find markerData variable in page")

    js_array = match.group(1)
    json_str = _convert_js_to_json(js_array)
    return json.loads(json_str)


def _convert_js_to_json(js_str: str) -> str:
    js_str = re.sub(r"([{,]\s*)(\w+):", r'\1"\2":', js_str)
    js_str = js_str.replace("'", '"')
    js_str = re.sub(r",\s*]", "]", js_str)
    js_str = re.sub(r",\s*}", "}", js_str)
    return js_str
