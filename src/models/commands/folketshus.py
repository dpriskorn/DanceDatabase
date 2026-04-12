import logging
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel

import config

logger = logging.getLogger(__name__)

API_URL = "https://www.folketshusochparker.se/wp-content/themes/fhp/inc/ajax.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:149.0) Gecko/20100101 Firefox/149.0",
    "Accept": "*/*",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.folketshusochparker.se/medlemmar/",
}


class FolketshusVenue(BaseModel):
    name: str
    url: str
    lat: float
    lng: float
    region: str


def fetch_members() -> list[FolketshusVenue]:
    response = requests.post(
        API_URL,
        data={"action": "get_members", "type": "member", "search": ""},
        headers=HEADERS,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("success"):
        raise ValueError(f"API returned success=false: {data}")
    html_fragments = data.get("data", {}).get("results", [])
    venues = []
    for html in html_fragments:
        venue = parse_venue(html)
        if venue:
            venues.append(venue)
    logger.info(f"Parsed {len(venues)} venues from {len(html_fragments)} HTML fragments")
    return venues


def parse_venue(html: str) -> FolketshusVenue | None:
    soup = BeautifulSoup(html, "lxml")
    article = soup.find("article")
    if not article:
        return None
    lat = article.get("data-lat")
    lng = article.get("data-lng")
    if not lat or not lng:
        logger.warning("Missing coordinates in article")
        return None
    link = article.find("a", class_="card-body--link")
    if not link:
        return None
    title_attr = link.get("title", "")
    h3_tag = link.find("h3", class_="card-title")
    name = title_attr or (h3_tag.get_text(strip=True) if h3_tag else "")
    if not name:
        logger.warning("Missing venue name")
        return None
    url = link.get("href", "")
    region_div = link.find("div", class_="card-content")
    region = region_div.get_text(strip=True) if region_div else ""
    return FolketshusVenue(name=name, url=url, lat=float(lat), lng=float(lng), region=region)


def run(date_str: str | None = None) -> None:
    logger.info("Fetching folketshus och parker venues...")
    venues = fetch_members()
    print(f"Found {len(venues)} venues.")

    output_dir = Path("data") / "folketshus" / "unmatched"
    output_dir.mkdir(parents=True, exist_ok=True)

    date_val = date_str or date.today().strftime("%Y-%m-%d")
    output_file = output_dir / f"{date_val}.json"

    import json

    output_file.write_text(json.dumps([v.model_dump() for v in venues], indent=2, ensure_ascii=False) + "\n")
    print(f"Saved to {output_file}")