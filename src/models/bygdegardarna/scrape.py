import json
import re
from typing import List, Dict, Any

import requests


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
