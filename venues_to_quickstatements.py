#!/usr/bin/env python3
"""
Generate QuickStatements v1 file for unmapped venues.

Reads from data/unmapped_venues_2026_april.json and writes to data/danslogen_venues_qs.txt
in QuickStatements v1 format.
"""
import json
import sys
from pathlib import Path
from urllib.parse import quote

import click

sys.path.insert(0, str(__file__).rsplit('/', 1)[0])


def main():
    input_path = Path("data/unmapped_venues_2026_april.json")
    output_path = Path("data/danslogen_venues_qs.txt")

    with open(input_path) as f:
        venues = json.load(f)

    with open(output_path, "w", encoding="utf-8") as qs:
        for i, venue_info in enumerate(venues, start=1):
            venue_name = venue_info["venue"]
            ort = venue_info.get("ort", "")
            kommun = venue_info.get("kommun", "")

            search_query = quote(f"{venue_name}, {kommun}" if kommun else venue_name)
            osm_url = f"https://www.openstreetmap.org/search?query={search_query}"
            google_url = f"https://www.google.com/maps/search/{search_query}"

            print(f"[{i}/{len(venues)}] {venue_name} ({kommun})")
            print(f"  OSM:  {osm_url}")
            print(f"  Google: {google_url}")

            coord_str = click.prompt("  Coordinates (lat/lon or Enter to skip)", default="", show_default=False)

            qs.write("CREATE\n")
            qs.write(f'LAST\tLsv\t"{venue_name}"\n')
            qs.write(f'LAST\tDsv\t"dansställe"\n')
            qs.write(f'LAST\tP1\tQ20\n')
            if coord_str:
                coord_clean = coord_str.replace(',', '/').replace(' ', '/')
                qs.write(f'LAST\tP4\t@{coord_clean}\n')
            qs.write("\n")

    print(f"\nWrote {len(venues)} venues to {output_path}")


if __name__ == "__main__":
    main()
