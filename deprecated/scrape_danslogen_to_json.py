import json
import logging
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(__file__).rsplit('/', 1)[0])

from src.models.danslogen.table_row import DanslogenTableRow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_html(month: str) -> BeautifulSoup:
    url = f"https://www.danslogen.se/dansprogram/{month}"
    response = requests.get(url)
    response.raise_for_status()
    logger.info("Fetched page: %s", url)
    return BeautifulSoup(response.text, "lxml")


def parse_rows(soup: BeautifulSoup) -> list[DanslogenTableRow]:
    table = soup.find("table", class_="danceprogram")
    if not table:
        raise Exception("No danceprogram table found")

    rows = table.select("tr[class^='r']")
    logger.info("Found %d rows", len(rows))

    parsed_rows: list[DanslogenTableRow] = []
    for i, row in enumerate(rows, start=1):
        table_row = DanslogenTableRow.from_row(row)
        if table_row:
            parsed_rows.append(table_row)
            logger.debug("Row %d: %s", i, table_row.model_dump())
        else:
            logger.debug("Row %d: skipped (invalid or empty)", i)

    logger.info("Parsed %d valid rows", len(parsed_rows))
    return parsed_rows


def write_json(rows: list[DanslogenTableRow], month: str, year: int = 2026) -> Path:
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)

    output_path = output_dir / f"danslogen_rows_{year}_{month}.json"

    data = [row.model_dump() for row in rows]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info("Wrote %d rows to %s", len(data), output_path)
    return output_path


def scrape(month: str = "april", year: int = 2026) -> Path:
    soup = fetch_html(month)
    rows = parse_rows(soup)
    output_path = write_json(rows, month, year)
    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scrape Danslogen dance program to JSON")
    parser.add_argument("--month", default="april", help="Month to scrape (default: april)")
    parser.add_argument("--year", type=int, default=2026, help="Year to scrape (default: 2026)")
    args = parser.parse_args()

    output_path = scrape(args.month, args.year)
    print(f"Wrote rows to: {output_path}")
