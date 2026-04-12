#!/usr/bin/env python3
"""
Generate QuickStatements v1 file for unmapped bands.

Reads from data/unmapped_bands_2026_april.json and writes to data/danslogen_bands_qs.txt
in QuickStatements v1 format.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(__file__).rsplit('/', 1)[0])

ARTIST_QID = "Q225"


def main():
    input_path = Path("data/unmapped_bands_2026_april.json")
    output_path = Path("data/danslogen_bands_qs.txt")

    with open(input_path) as f:
        bands = json.load(f)

    with open(output_path, "w", encoding="utf-8") as qs:
        for band_info in bands:
            band_name = band_info["band"]
            qs.write("CREATE\n")
            qs.write(f'LAST\tLsv\t"{band_name}"\n')
            qs.write(f'LAST\tDsv\t"artist"\n')
            qs.write(f"LAST\tP1\t{ARTIST_QID}\n\n")

    print(f"Wrote {len(bands)} bands to {output_path}")


if __name__ == "__main__":
    main()
