"""Wikidata operations: fetch artists."""
import json
from datetime import date

import config as root_config
from src.models.dancedb.config import config as dancedb_config
from src.models.dancedb_client import DancedbClient, wbi_config


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

    output_file = dancedb_config.wikidata_dir / "artists" / f"{date_str}.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(artists, f, ensure_ascii=False, indent=2)

    print(f"Saved to {output_file}")


def match_wikidata_artists(date_str: str | None = None, dry_run: bool = False) -> None:
    """Match DanceDB artists to Wikidata and upload P3 (Wikidata QID) as external ID."""
    from rapidfuzz import process as fuzz_process

    date_str = date_str or date.today().strftime("%Y-%m-%d")
    print("\n=== Match Wikidata artists to DanceDB ===")

    wikidata_file = dancedb_config.wikidata_dir / "artists" / f"{date_str}.json"
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