#!/usr/bin/env python3
"""
Upload unmapped bands to DanceDB.

Reads from data/unmapped_bands_2026_april.json, searches/creates bands on DanceDB,
and saves the updated QID mappings to src/models/danslogen/maps.py.
"""
import argparse
import json
import logging
import re
import sys
from pathlib import Path

import questionary

sys.path.insert(0, str(__file__).rsplit('/', 1)[0])

from src.models.dancedb_client import DancedbClient
from src.models.danslogen.maps import BAND_QID_MAP

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def save_bands_to_maps(new_bands: dict[str, str]) -> None:
    """Save updated BAND_QID_MAP to maps.py."""
    if not new_bands:
        print("No new bands to save.")
        return

    maps_path = Path(__file__).parent / 'src' / 'models' / 'danslogen' / 'maps.py'
    
    with open(maps_path) as f:
        content = f.read()

    for band_name, qid in new_bands.items():
        escaped_name = re.escape(band_name)
        if re.search(rf'"{escaped_name}"\s*:', content):
            logger.warning("Band '%s' already exists in BAND_QID_MAP, skipping", band_name)
            continue

        insert_pattern = r'(BAND_QID_MAP: dict\[str, str\] = \{)'
        insert_replacement = rf'\1\n    "{band_name}": "{qid}",'
        
        new_content = re.sub(insert_pattern, insert_replacement, content)
        
        if new_content == content:
            logger.error("Could not find insertion point for '%s'", band_name)
            continue

        content = new_content
        logger.info("Added '%s' to maps.py", band_name)

    with open(maps_path, 'w') as f:
        f.write(content)

    print(f"Saved {len(new_bands)} new QIDs to {maps_path}")


def main():
    parser = argparse.ArgumentParser(description="Upload unmapped bands to DanceDB")
    parser.add_argument("--input", "-i", "input_file",
                        default="data/unmapped_bands_2026_april.json",
                        help="Input JSON file with unmapped bands")
    parser.add_argument("--dry-run", action="store_true", default=False,
                        help="Search but do not create bands on DanceDB")
    parser.add_argument("--limit", "-l", type=int, default=None,
                        help="Limit number of bands to process")
    args = parser.parse_args()
    input_file = args.input_file
    dry_run = args.dry_run
    limit = args.limit
    """
    Upload unmapped bands to DanceDB.

    Reads bands from INPUT_FILE, searches/creates them on DanceDB,
    and saves updated QID mappings.
    """
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    with open(input_path) as f:
        bands = json.load(f)

    if limit:
        bands = bands[:limit]

    print(f"Processing {len(bands)} bands from {input_file}")

    if dry_run:
        print("DRY RUN - no changes will be made to DanceDB\n")

    client = None
    if not dry_run:
        client = DancedbClient()

    found = []
    created = []
    skipped = []

    for i, band_info in enumerate(bands):
        band_name = band_info['band']
        count = band_info.get('count', 0)
        existing_qid = next((qid for key, qid in BAND_QID_MAP.items()
                            if key.lower() == band_name.lower()), None)
        if existing_qid:
            print(f"[{i+1}/{len(bands)}] {band_name} ({count} events) → {existing_qid} (already mapped)")
            found.append((band_name, existing_qid))
            continue

        if dry_run:
            print(f"[{i+1}/{len(bands)}] {band_name} ({count} events) → NOT FOUND (would create)")
            skipped.append(band_name)
            continue

        qid = client.search_band(band_name)
        if qid:
            print(f"[{i+1}/{len(bands)}] {band_name} ({count} events) → {qid} (found)")
            found.append((band_name, qid))
            BAND_QID_MAP[band_name] = qid
        else:
            try:
                new_qid = client.create_band(band_name)
                if new_qid:
                    url = f"https://dance.wikibase.cloud/wiki/Item:{new_qid}"
                    print(f"[{i+1}/{len(bands)}] {band_name} ({count} events) → {new_qid} (created)")
                    print(f"  → {url}")
                    created.append((band_name, new_qid))
                    BAND_QID_MAP[band_name] = new_qid
                else:
                    print(f"[{i+1}/{len(bands)}] {band_name} ({count} events) → SKIPPED (user declined)")
                    skipped.append(band_name)
            except KeyboardInterrupt:
                print("\nAborted by user.")
                break

    print(f"\n{'='*50}")
    if dry_run:
        print(f"DRY RUN SUMMARY:")
        print(f"  Already mapped: {len(found)}")
        print(f"  Would create: {len(skipped)}")
    else:
        print(f"SUMMARY:")
        print(f"  Found on DanceDB: {len(found)}")
        print(f"  Created: {len(created)}")
        print(f"  Skipped: {len(skipped)}")
        
        if created:
            save_bands_to_maps(dict(created))
        else:
            print("No new bands to save.")


if __name__ == '__main__':
    main()
