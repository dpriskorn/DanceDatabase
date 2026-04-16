"""Ensure onbeat venues exist in DanceDB."""
import json
import logging
import sys
import urllib.parse
from datetime import date
from pathlib import Path

import questionary

import config
from src.models.dancedb.ensure import create_venue
from src.utils.coords import parse_coords

logger = logging.getLogger(__name__)


def onbeat_ensure_venues(date_str: str | None = None, dry_run: bool = False) -> None:
    """Ensure onbeat venues exist in DanceDB."""
    date_str = date_str or date.today().strftime("%Y-%m-%d")
    print(f"\n=== Ensuring onbeat venues exist for {date_str} ===")

    onbeat_file = config.onbeat_dir / f"{date_str}.json"
    if not onbeat_file.exists():
        print(f"Error: onbeat data not found: {onbeat_file}")
        print("Run 'scrape-onbeat' first to fetch events.")
        return

    onbeat_data = json.loads(onbeat_file.read_text())
    events = onbeat_data.get("events", [])
    print(f"Loaded {len(events)} events from {onbeat_file}")

    dancedb_file = config.dancedb_venues_dir / "2026-04-12.json"
    if dancedb_file.exists():
        dancedb_venues = json.loads(dancedb_file.read_text())
    else:
        dancedb_venues = {}
    print(f"Loaded {len(dancedb_venues)} venues from DanceDB")

    folketshus_file = config.folketshus_enriched_dir / "2026-04-14.json"
    if folketshus_file.exists():
        folketshus_data = json.loads(folketshus_file.read_text())
        folketshus_venues = {v["name"].lower(): v for v in folketshus_data if v.get("qid")}
    else:
        folketshus_venues = {}
    print(f"Loaded {len(folketshus_venues)} venues from Folketshus")

    bygdegard_file = config.bygdegardarna_dir / "2026-04-14.json"
    if bygdegard_file.exists():
        bygdegard_venues = json.loads(bygdegard_file.read_text())
    else:
        bygdegard_venues = []
    print(f"Loaded {len(bygdegard_venues)} venues from Bygdegardarna")

    venues_needed: dict[str, dict] = {}
    for event in events:
        venue_name = event.get("location", "")
        if not venue_name:
            continue

        venue_qid = event.get("venue_qid", "")
        if venue_qid:
            continue

        if venue_name not in venues_needed:
            venues_needed[venue_name] = {"source": None, "coords": None, "external_id": None}

    print(f"Found {len(venues_needed)} venues needing QIDs")

    if not venues_needed:
        print("All venues have QIDs!")
        return

    for venue_name, info in venues_needed.items():
        venue_lower = venue_name.lower()

        matched = False
        for qid, v in dancedb_venues.items():
            label = v.get("label", "").lower()
            if venue_lower in label or label in venue_lower:
                print(f"  {venue_name} -> DanceDB: {v['label']} ({qid})")
                info["source"] = "dancedb"
                info["qid"] = qid
                matched = True
                break
            aliases = v.get("aliases", [])
            for alias in aliases:
                if venue_lower in alias or alias in venue_lower:
                    print(f"  {venue_name} -> DanceDB alias: {alias} ({qid})")
                    info["source"] = "dancedb"
                    info["qid"] = qid
                    matched = True
                    break
            if matched:
                break

        if matched:
            continue

        for name, v in folketshus_venues.items():
            if venue_lower in name or name in venue_lower:
                print(f"  {venue_name} -> Folketshus: {v['name']} ({v.get('qid')})")
                info["source"] = "folketshus"
                info["qid"] = v.get("qid")
                info["external_id"] = v.get("external_id")
                matched = True
                break

        if matched:
            continue

        for v in bygdegard_venues:
            title = v.get("title", "").lower()
            if venue_lower in title or title in venue_lower:
                pos = v.get("position", {})
                print(f"  {venue_name} -> Bygdegardarna: {v['title']}")
                info["source"] = "bygdegardarna"
                info["coords"] = {"lat": pos.get("lat"), "lng": pos.get("lng")}
                info["external_id"] = v["meta"].get("permalink", "")
                matched = True
                break

    venues_to_create = {n: i for n, i in venues_needed.items() if not i.get("qid") and not i.get("source") == "dancedb"}
    print(f"\n{len(venues_to_create)} venues need to be created in DanceDB")

    if not venues_to_create:
        print("All venues resolved!")
        return

    from src.models.dancedb.client import DancedbClient

    for venue_name, info in venues_to_create.items():
        print(f"\n--- {venue_name} ---")
        source = info.get("source", "unknown")
        print(f"Source: {source}")

        coords = info.get("coords")
        if not coords:
            gmaps = f'https://www.google.com/search?q={urllib.parse.quote(venue_name, safe="")}'
            print(f"Google: {gmaps}")

        try:
            confirm = questionary.select(
                f"Create venue '{venue_name}' in DanceDB?", choices=["Yes (Recommended)", "No", "Abort"]
            ).ask()
        except Exception:
            print("Non-interactive mode - skipping creation")
            continue

        if confirm == "No":
            print("Skipping...")
            continue
        elif confirm == "Abort":
            print("Aborting...")
            sys.exit(0)
            continue

        if not coords:
            print("Enter coordinates (lat, lng) or press Enter to skip:")
            try:
                coords_input = input("> ").strip()
                if coords_input:
                    coords = parse_coords(coords_input)
            except Exception:
                print("Invalid format, skipping")
                continue

        if not coords:
            print("No coordinates - skipping")
            continue

        external_ids = {}
        if info.get("external_id"):
            external_ids["P44"] = info["external_id"]

        if dry_run:
            print(f"[DRY RUN] Would create: {venue_name} at {coords}")
            if external_ids:
                print(f"  External IDs: {external_ids}")
            continue

        db_client = DancedbClient()
        qid = create_venue(venue_name, coords["lat"], coords["lng"], external_ids=external_ids, client=db_client)
        if qid:
            print(f"Created: https://dance.wikibase.cloud/wiki/Item:{qid}")
            info["qid"] = qid
            info["source"] = "created"
        else:
            print("Failed to create venue")

    print("\nDone!")
