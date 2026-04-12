#!/usr/bin/env python3
"""update_bygdegardarna_venues.py - Update DanceDB venues with bygdegardarna data.

Adds P42 (Bygdegårdarnas Riksförbund ID) and aliases to matched venues.
"""
import json
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import questionary

import config
from wikibaseintegrator import WikibaseIntegrator
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator.wbi_login import Login

wbi_config['MEDIAWIKI_API_URL'] = 'https://dance.wikibase.cloud/w/api.php'
wbi_config['SPARQL_ENDPOINT_URL'] = 'https://dance.wikibase.cloud/query/sparql'
wbi_config['WIKIBASE_URL'] = 'https://dance.wikibase.cloud'

ENRICHED_DIR = Path("data") / "bygdegardarna" / "enriched"
DANCEDB_VENUES_DIR = Path("data") / "dancedb" / "venues"


def is_interactive() -> bool:
    """Check if running in interactive terminal."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def extract_bygdegardarna_id(permalink: str) -> str:
    """Extract ID from bygdegardarna permalink."""
    path = urlparse(permalink).path
    segments = path.strip("/").split("/")
    return segments[-1] if segments else ""


def load_enriched_venues(date_str: str) -> list[dict]:
    """Load enriched venues for given date."""
    path = ENRICHED_DIR / f"{date_str}.json"
    if not path.exists():
        raise FileNotFoundError(f"Enriched venues not found: {path}")
    return json.loads(path.read_text())


def load_dancedb_venues(date_str: str) -> dict[str, dict]:
    """Load DanceDB venues for given date."""
    path = DANCEDB_VENUES_DIR / f"{date_str}.json"
    if not path.exists():
        raise FileNotFoundError(f"DanceDB venues not found: {path}")
    return json.loads(path.read_text())


def update_venue(qid: str, byg_title: str, permalink: str, db_label: str, dry_run: bool, wbi: WikibaseIntegrator) -> None:
    """Update a single DanceDB venue with P42 and alias."""
    from wikibaseintegrator import datatypes
    from wikibaseintegrator.entities.item import ItemEntity

    byg_id = extract_bygdegardarna_id(permalink)
    alias_needed = byg_title.lower() != db_label.lower()

    print(f"  Label (DanceDB): \"{db_label}\"")
    print(f"  P42: \"{byg_id}\" (NEW)")
    print(f"  Alias: \"{byg_title}\" ({'NEW' if alias_needed else 'same as label'})")

    if dry_run:
        print("  [DRY RUN - skipped]")
        return

    item = ItemEntity(id=qid)
    item.get()

    item.claims.add(datatypes.ExternalID(prop_nr="P42", value=byg_id))

    if alias_needed:
        current_aliases = item.aliases.get("sv") or []
        if byg_title not in current_aliases:
            new_aliases = current_aliases + [byg_title]
            item.aliases.set("sv", new_aliases)

    item.write(login=wbi.login)

    base_url = "https://dance.wikibase.cloud"
    print(f"  Uploaded: {base_url}/wiki/{qid}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Update DanceDB venues with bygdegardarna data")
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    parser.add_argument("--start", type=int, default=1, help="Start from venue N")
    parser.add_argument("--date", default=None, help="Date for input files (YYYY-MM-DD, default: today)")
    args = parser.parse_args()

    date_str = args.date or date.today().strftime("%Y-%m-%d")

    print(f"Loading data for {date_str}...")
    enriched = load_enriched_venues(date_str)
    db_venues = load_dancedb_venues(date_str)
    print(f"Loaded {len(enriched)} enriched venues, {len(db_venues)} DanceDB venues")

    wbi = None
    if not args.dry_run:
        login = Login(user=config.username, password=config.password)
        wbi = WikibaseIntegrator(login=login)

    total = len(enriched)
    skipped = 0
    uploaded = 0
    skip_all = False

    for i, venue in enumerate(enriched, start=1):
        if i < args.start:
            continue

        qid = venue.get("qid")
        if not qid:
            print(f"[{i}/{total}] Skipping - no QID")
            skipped += 1
            continue

        byg_title = venue.get("title", "")
        permalink = venue.get("permalink", "")

        db_label = db_venues.get(qid, {}).get("label", "")

        print(f"\n[{i}/{total}] {byg_title} → {qid}")

        if skip_all:
            print("  Skipping (skip all)")
            skipped += 1
            continue

        if args.dry_run:
            print("  [DRY RUN - would update]")
            print(f"    Label (DanceDB): \"{db_label}\"")
            print(f"    P42: \"{extract_bygdegardarna_id(permalink)}\"")
            print(f"    Alias: \"{byg_title}\"")
            skipped += 1
            continue

        if is_interactive():
            choice = questionary.rawselect(
                f"Upload to DanceDB?",
                choices=["Yes (Recommended)", "Skip", "Skip all", "Abort"]
            ).ask()

            if choice == "Skip":
                skipped += 1
                continue
            elif choice == "Skip all":
                print("Skipping remaining venues...")
                skip_all = True
                continue
            elif choice == "Abort":
                print("Aborting...")
                sys.exit(0)
        else:
            print("  Non-interactive mode - uploading automatically")
            print(f"    Label (DanceDB): \"{db_label}\"")
            print(f"    P42: \"{extract_bygdegardarna_id(permalink)}\"")
            print(f"    Alias: \"{byg_title}\"")

        update_venue(qid, byg_title, permalink, db_label, args.dry_run, wbi)
        uploaded += 1
        time.sleep(1)

    print(f"\nDone. Processed: {total}, Uploaded: {uploaded}, Skipped: {skipped}")


if __name__ == "__main__":
    main()