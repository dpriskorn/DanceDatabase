"""Venue operations: scrape, match, ensure exist."""
import json
import logging
import sys
from datetime import date

from rapidfuzz import process as fuzz_process

import config
from src.models.dancedb.scrape import scrape_bygdegardarna, scrape_dancedb_venues
from src.models.dancedb.match import match_venues
from src.models.dancedb.ensure import ensure_venues, create_venue
from src.models.dancedb.ensure_onbeat import onbeat_ensure_venues
from src.models.dancedb.client import DancedbClient

logger = logging.getLogger(__name__)


def ensure_artists(date_str: str | None = None, dry_run: bool = False) -> None:
    """Ensure danslogen artists exist in DanceDB before uploading events."""
    date_str = date_str or date.today().strftime("%Y-%m-%d")
    date.strptime(date_str, "%Y-%m-%d").strftime("%B").lower()
    print(f"\n=== Ensuring artists exist for {date_str} ===")

    dansevents_file = config.danslogen_dir / "artists" / f"{date_str}.json"
    if not dansevents_file.exists():
        print(f"Error: danslogen data not found: {dansevents_file}")
        return

    client = DancedbClient()
    existing_artists = client.fetch_artists_from_dancedb()
    existing_labels = {a.get("label", "").lower(): a for a in existing_artists if a.get("label")}
    print(f"Found {len(existing_artists)} artists in DanceDB")

    events = json.loads(dansevents_file.read_text())
    artists_needed = set(e.get("artist_name") or e.get("band") for e in events if e.get("artist_name") or e.get("band"))
    print(f"Need artists for {len(artists_needed)} unique artists")

    new_artists = []
    matched = 0
    for artist_name in artists_needed:
        if not artist_name:
            continue
        artist_lower = artist_name.lower()
        if artist_lower in existing_labels:
            matched += 1
            continue
        alias_match = False
        for existing in existing_artists:
            aliases = existing.get("aliases", [])
            for alias in aliases:
                if fuzz_process.extractOne(artist_lower, [alias], score_cutoff=80):
                    alias_match = True
                    break
            if alias_match:
                break
        if alias_match:
            matched += 1
            continue
        fuzzy = fuzz_process.extractOne(artist_lower, list(existing_labels.keys()), score_cutoff=80)
        if fuzzy:
            logger.info(f"Fuzzy matched '{artist_name}' to '{fuzzy[0]}' ({fuzzy[1]}%)")
            matched += 1
            continue
        new_artists.append(artist_name)

    print(f"Matched: {matched}")
    print(f"Need to create: {len(new_artists)}")

    if not new_artists:
        print("All artists exist in DanceDB!")
        return

    print(f"\nMissing artists: {new_artists[:20]}...")
    if len(new_artists) > 20:
        print(f"  ... and {len(new_artists) - 20} more")

    if dry_run:
        for artist_name in new_artists:
            print(f"[DRY RUN] Would create: {artist_name}")
        return

    for artist_name in new_artists[:10]:
        print(f"\n--- Creating artist: {artist_name} ---")
        print("Enter spelplan_id or press Enter to skip:")
        spelplan_id = input("> ").strip()

        if not spelplan_id:
            print("Skipping artist creation")
            continue

        try:
            qid = client.get_or_create_band(artist_name, spelplan_id=spelplan_id)
            if qid:
                print(f"Created: https://dance.wikibase.cloud/wiki/Item:{qid}")
                existing_labels[artist_name.lower()] = {"qid": qid, "label": artist_name}
            else:
                print("Failed to create artist")
        except Exception as e:
            print(f"Error creating artist: {e}")

    print("\nArtist matching done.")
