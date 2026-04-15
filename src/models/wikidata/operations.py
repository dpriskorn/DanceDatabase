"""Wikidata operations: fetch and match artists."""
import json
import logging
from datetime import date

import questionary
import config as root_config
from src.models.dancedb.client import DancedbClient, wbi_config

logger = logging.getLogger(__name__)


def scrape_wikidata_artists(date_str: str | None = None) -> None:
    """Fetch all known Swedish folk dance artists from Wikidata."""
    from wikibaseintegrator.wbi_helpers import execute_sparql_query

    date_str = date_str or date.today().strftime("%Y-%m-%d")
    print("\n=== Scrape Wikidata artists ===")

    wbi_config["USER_AGENT"] = root_config.user_agent

    sparql = """
    SELECT ?o ?oLabel WHERE {
      {
        ?o wdt:P136 wd:Q1164847 .
      }
      UNION
      {
        ?o wdt:P31 wd:Q1164847 .
      }

      SERVICE wikibase:label {
        bd:serviceParam wikibase:language "[AUTO_LANGUAGE],sv,en".
      }
    }
    LIMIT 5000
    """

    endpoint = "https://query.wikidata.org/sparql"
    results = execute_sparql_query(query=sparql, endpoint=endpoint)

    artists = {}
    for binding in results["results"]["bindings"]:
        qid = binding["o"]["value"].rsplit("/", 1)[-1]
        label = binding.get("oLabel", {}).get("value", "")
        artists[qid] = {"label": label}

    print(f"Found {len(artists)} artists")

    output_file = root_config.wikidata_dir / "artists" / f"{date_str}.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(artists, f, ensure_ascii=False, indent=2)

    print(f"Saved to {output_file}")


def match_wikidata_artists(date_str: str | None = None, dry_run: bool = False) -> None:
    """Match DanceDB artists to Wikidata and upload P3 (Wikidata QID) as external ID."""
    from rapidfuzz import process as fuzz_process

    date_str = date_str or date.today().strftime("%Y-%m-%d")
    print("\n=== Match Wikidata artists to DanceDB ===")

    wikidata_file = root_config.wikidata_dir / "artists" / f"{date_str}.json"
    if not wikidata_file.exists():
        print(f"Error: Wikidata artists file not found: {wikidata_file}")
        return

    wikidata_artists = json.loads(wikidata_file.read_text())
    print(f"Loaded {len(wikidata_artists)} Wikidata artists")

    wikidata_labels = {v["label"].lower(): qid for qid, v in wikidata_artists.items()}
    wikidata_label_list = list(wikidata_labels.keys())

    client = DancedbClient()
    dancedb_artists = client.fetch_artists_from_dancedb()
    print(f"Found {len(dancedb_artists)} artists in DanceDB")

    matched = []
    unmatched = []

    for artist in dancedb_artists:
        db_label = artist.get("label", "").lower()
        db_qid = artist.get("qid")

        if db_label in wikidata_labels:
            wd_qid = wikidata_labels[db_label]
            matched.append((artist, wd_qid))
            print(f"Exact match: '{artist.get('label')}' -> {wd_qid}")
        else:
            fuzzy = fuzz_process.extractOne(
                db_label, wikidata_label_list, score_cutoff=85
            )
            if fuzzy:
                wd_qid = wikidata_labels[fuzzy[0]]
                matched.append((artist, wd_qid))
                print(
                    f"Fuzzy match: '{artist.get('label')}' -> '{fuzzy[0]}' "
                    f"({fuzzy[1]}%) -> {wd_qid}"
                )
            else:
                unmatched.append(artist)

    print(f"\nMatched: {len(matched)}")
    print(f"Unmatched: {len(unmatched)}")

    if not matched:
        print("No matches found.")
        return

    print("\n--- Uploading P3 to DanceDB ---")
    from wikibaseintegrator import datatypes

    for artist, wd_qid in matched:
        db_qid = artist.get("qid")
        db_label = artist.get("label")

        if dry_run:
            print(f"[DRY RUN] Would add P3={wd_qid} to {db_label} ({db_qid})")
            continue

        print(f"Adding P3={wd_qid} to {db_label} ({db_qid})...")
        item = client.wbi.item.get(entity_id=db_qid)
        item.claims.add(datatypes.String(prop_nr="P3", value=wd_qid))
        item.write(login=client.wbi.login, summary="Add Wikidata QID from matching")
        print(f"  Updated: {client.base_url}/wiki/Item:{db_qid}")


def sync_wikidata_artists(
    date_str: str | None = None,
    month: str = "april",
    year: int = 2026,
    dry_run: bool = False,
) -> None:
    """Create missing artists from danslogen and add P3 to artists without P3."""
    from rapidfuzz import process as fuzz_process
    from wikibaseintegrator import datatypes

    date_str = date_str or date.today().strftime("%Y-%m-%d")
    print("\n=== Sync Wikidata artists from Danslogen ===")

    wikidata_file = root_config.wikidata_dir / "artists" / f"{date_str}.json"
    if not wikidata_file.exists():
        print(f"Error: Wikidata artists file not found: {wikidata_file}")
        return

    wikidata_artists = json.loads(wikidata_file.read_text())
    print(f"Loaded {len(wikidata_artists)} Wikidata artists")

    wikidata_labels = {v["label"].lower(): qid for qid, v in wikidata_artists.items()}
    wikidata_label_list = list(wikidata_labels.keys())

    client = DancedbClient()
    dancedb_artists = client.fetch_artists_from_dancedb()
    dancedb_labels = {a.get("label", "").lower(): a for a in dancedb_artists}
    artists_with_p3 = {a.get("qid") for a in dancedb_artists if a.get("p3")}
    print(f"Found {len(dancedb_artists)} artists in DanceDB, {len(artists_with_p3)} have P3")

    from src.models.danslogen.data import load_band_map
    danslogen_bands = set(load_band_map().keys())
    print(f"Found {len(danslogen_bands)} bands in danslogen (from DanceDB artists)")

    missing_bands = []
    needs_p3 = []

    dancedb_label_list = list(dancedb_labels.keys())
    for band in danslogen_bands:
        band_lower = band.lower()
        wd_qid = None

        if band_lower in wikidata_labels:
            wd_qid = wikidata_labels[band_lower]
        else:
            fuzzy = fuzz_process.extractOne(
                band_lower, wikidata_label_list, score_cutoff=85
            )
            if fuzzy:
                wd_qid = wikidata_labels[fuzzy[0]]

        found_db = None
        if band_lower in dancedb_labels:
            found_db = dancedb_labels[band_lower]
        else:
            fuzzy_db = fuzz_process.extractOne(
                band_lower, dancedb_label_list, score_cutoff=80
            )
            if fuzzy_db:
                found_db = dancedb_labels[fuzzy_db[0]]
                logger.info(f"Fuzzy matched band '{band}' to DanceDB '{fuzzy_db[0]}' ({fuzzy_db[1]}%)")
            else:
                for existing in dancedb_labels.values():
                    aliases = existing.get("aliases", [])
                    for alias in aliases:
                        if fuzz_process.extractOne(band_lower, [alias], score_cutoff=80):
                            found_db = existing
                            logger.info(f"Fuzzy matched band '{band}' to alias '{alias}' ({80}%)")
                            break
                    if found_db:
                        break

        if not found_db:
            missing_bands.append({"name": band, "wd_qid": wd_qid})
        else:
            db_qid = found_db.get("qid")
            if wd_qid and db_qid and db_qid not in artists_with_p3:
                needs_p3.append({"name": band, "db_qid": db_qid, "wd_qid": wd_qid})

    print(f"Missing in DanceDB: {len(missing_bands)}")
    print(f"Need P3 added: {len(needs_p3)}")

    if not missing_bands and not needs_p3:
        print("All bands already in DanceDB with P3!")
        return

    skip_all = False
    abort = False

    if needs_p3:
        print("\n--- Adding P3 to existing artists ---")
        for band_data in needs_p3:
            band_name = band_data["name"]
            db_qid = band_data["db_qid"]
            wd_qid = band_data["wd_qid"]

            print(f"\n{band_name} ({db_qid}) -> Wikidata {wd_qid}")

            if dry_run:
                print(f"[DRY RUN] Would add P3={wd_qid}")
                continue

            if skip_all:
                print("Skipping (skip all)")
                continue

            response = questionary.select(
                f"Add P3={wd_qid} to {band_name}?",
                choices=["Yes", "Skip", "Skip all", "Abort"],
            ).ask()

            if response == "Yes":
                print(f"Adding P3={wd_qid} to {band_name} ({db_qid})...")
                item = client.wbi.item.get(entity_id=db_qid)
                item.claims.add(datatypes.String(prop_nr="P3", value=wd_qid))
                item.write(login=client.wbi.login, summary="Add Wikidata QID from sync")
                print(f"  Updated: {client.base_url}/wiki/Item:{db_qid}")
            elif response == "Skip":
                print("Skipped")
            elif response == "Skip all":
                print("Skipping all remaining")
                skip_all = True
            elif response == "Abort":
                print("Aborting")
                abort = True
                break

    if abort:
        print("\nAborted by user")
        return

    skip_all = False

    if missing_bands:
        print("\n--- Creating missing artists ---")
        for band_data in missing_bands:
            band_name = band_data["name"]
            wd_qid = band_data["wd_qid"]

            print(f"\n{band_name}")
            if wd_qid:
                print(f"  Wikidata match: {wd_qid}")

            if dry_run:
                if wd_qid:
                    print(f"[DRY RUN] Would create artist with P3={wd_qid}")
                else:
                    print("[DRY RUN] Would create artist (no Wikidata match)")
                continue

            if skip_all:
                print("Skipping (skip all)")
                continue

            choices = ["Yes"]
            if wd_qid:
                choices.append("Yes + add P3")
            choices.extend(["Skip", "Skip all", "Abort"])

            response = questionary.select(
                f"Create artist '{band_name}' in DanceDB?",
                choices=choices,
            ).ask()

            if response and "Yes" in response:
                add_p3 = "add P3" in response and wd_qid is not None
                print(f"Creating artist: {band_name}...")
                new_item = client.wbi.item.new()
                new_item.labels.set("sv", band_name)
                new_item.labels.set("en", band_name)
                new_item.claims.add(datatypes.Item(prop_nr="P1", value="Q225"))

                if add_p3:
                    new_item.claims.add(datatypes.String(prop_nr="P3", value=wd_qid))
                    print(f"  Added P3={wd_qid}")

                summary = "Create artist from danslogen sync"
                if wd_qid:
                    summary += f" with Wikidata {wd_qid}"

                new_item.write(
                    login=client.wbi.login,
                    summary=summary,
                )
                qid = new_item.id
                print(f"  Created: {client.base_url}/wiki/Item:{qid}")

                dancedb_labels[band_name.lower()] = {"qid": qid, "label": band_name}
            elif response == "Skip":
                print("Skipped")
            elif response == "Skip all":
                print("Skipping all remaining")
                skip_all = True
            elif response == "Abort":
                print("Aborting")
                abort = True
                break

    if abort:
        print("\nAborted by user")
    else:
        print("\nDone!")