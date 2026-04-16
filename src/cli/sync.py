"""Sync workflow CLI commands."""
from src.cli.base import get_date_str, get_month_year


def add_sync_subparsers(sub) -> dict:
    """Add sync subparsers and return command handlers."""
    handlers = {}
    
    p = sub.add_parser("scrape-all", help="Scrape all data sources at once")
    p.add_argument("-m", "--month", default=None, help="Month name (default: current month)")
    p.add_argument("-y", "--year", type=int, default=None, help="Year (default: current year)")
    handlers["scrape-all"] = _scrape_all
    
    p = sub.add_parser("sync-danslogen", help="Sync danslogen: scrape → ensure-venues → upload")
    p.add_argument("-m", "--month", default=None, help="Month name (default: current month)")
    p.add_argument("-y", "--year", type=int, default=None, help="Year (default: current year)")
    p.add_argument("-l", "--limit", type=int, default=None, help="Limit number of events")
    p.add_argument("--only-scrape", action="store_true", help="Only scrape, skip uploads")
    handlers["sync-danslogen"] = _sync_danslogen
    
    p = sub.add_parser("sync-bygdegardarna", help="Sync bygdegardarna: scrape → fetch-dancedb → match")
    p.add_argument("--only-scrape", action="store_true", help="Only scrape, skip uploads")
    handlers["sync-bygdegardarna"] = _sync_bygdegardarna
    
    p = sub.add_parser("sync-onbeat", help="Sync onbeat: scrape + upload")
    handlers["sync-onbeat"] = _sync_onbeat
    
    p = sub.add_parser("sync-cogwork", help="Sync cogwork: scrape + upload")
    handlers["sync-cogwork"] = _sync_cogwork
    
    p = sub.add_parser("sync-folketshus", help="Sync folketshus: scrape + match")
    handlers["sync-folketshus"] = _sync_folketshus
    
    p = sub.add_parser("sync-all", help="Sync all sources in sequence")
    p.add_argument("-m", "--month", default=None, help="Month name (default: current month)")
    p.add_argument("-y", "--year", type=int, default=None, help="Year (default: current year)")
    p.add_argument("-l", "--limit", type=int, default=None, help="Limit number of events")
    p.add_argument("--only-scrape", action="store_true", help="Only scrape, skip uploads")
    handlers["sync-all"] = _sync_all
    
    p = sub.add_parser("scrape-bygdegardarna", help="Fetch bygdegardarna venues with coordinates")
    p.add_argument("-d", "--date", default=None, help="Date for output (YYYY-MM-DD, default: today)")
    handlers["scrape-bygdegardarna"] = _scrape_bygdegardarna
    
    p = sub.add_parser("scrape-dancedb-venues", help="Fetch existing venues from DanceDB")
    p.add_argument("-d", "--date", default=None, help="Date for output (YYYY-MM-DD, default: today)")
    handlers["scrape-dancedb-venues"] = _scrape_dancedb_venues
    
    p = sub.add_parser("match-bygdegardarna-venues", help="Match bygdegardarna venues to DanceDB")
    p.add_argument("-d", "--date", default=None, help="Date for input files (YYYY-MM-DD, default: today)")
    p.add_argument("--skip-prompts", action="store_true", help="Skip interactive prompts, auto-match fuzzy >=85")
    handlers["match-bygdegardarna-venues"] = _match_bygdegardarna_venues

    p = sub.add_parser("find-duplicate-venues", help="Find venues within 100m of each other")
    p.add_argument("-t", "--threshold", type=float, default=0.1, help="Distance threshold in km (default: 0.1 = 100m)")
    handlers["find-duplicate-venues"] = _find_duplicate_venues

    p = sub.add_parser("merge-duplicate-venues", help="Merge duplicate venues (close + similar names)")
    p.add_argument("-t", "--threshold", type=float, default=0.1, help="Distance threshold in km (default: 0.1 = 100m)")
    p.add_argument("--fuzzy", type=float, default=90, help="Fuzzy match threshold for label similarity (default: 90)")
    handlers["merge-duplicate-venues"] = _merge_duplicate_venues
    
    p = sub.add_parser("scrape-folketshus", help="Fetch folketshus och parker venues")
    p.add_argument("-d", "--date", default=None, help="Date for output (YYYY-MM-DD, default: today)")
    handlers["scrape-folketshus"] = _scrape_folketshus
    
    p = sub.add_parser("scrape-wikidata-artists", help="Fetch artists from Wikidata")
    p.add_argument("-d", "--date", default=None, help="Date for output (YYYY-MM-DD, default: today)")
    handlers["scrape-wikidata-artists"] = _scrape_wikidata_artists
    
    p = sub.add_parser("match-wikidata-artists", help="Match DanceDB artists to Wikidata")
    p.add_argument("-d", "--date", default=None, help="Date for Wikidata artists file (YYYY-MM-DD, default: today)")
    handlers["match-wikidata-artists"] = _match_wikidata_artists
    
    p = sub.add_parser("sync-wikidata-artists", help="Create missing artists from danslogen")
    p.add_argument("-d", "--date", default=None, help="Date for Wikidata artists file (YYYY-MM-DD, default: today)")
    p.add_argument("-m", "--month", default="april", help="Month name for danslogen (default: april)")
    p.add_argument("-y", "--year", type=int, default=2026, help="Year for danslogen (default: 2026)")
    handlers["sync-wikidata-artists"] = _sync_wikidata_artists
    
    return handlers


def _scrape_all(args) -> None:
    from src.models.dancedb.sync_all import scrape_all
    from src.cli.base import get_month_year
    month, year = get_month_year(args.month, args.year)
    scrape_all(month=month, year=year)


def _sync_danslogen(args) -> None:
    from src.models.dancedb.sync_danslogen import sync_danslogen, get_month_year
    month, year = get_month_year(args.month, args.year)
    sync_danslogen(
        month=month,
        year=year,
        limit=args.limit,
        only_scrape=args.only_scrape,
    )


def _sync_bygdegardarna(args) -> None:
    from src.models.dancedb.sync_bygdegardarna import sync_bygdegardarna
    sync_bygdegardarna(only_scrape=args.only_scrape)


def _sync_onbeat(args) -> None:
    from src.models.dancedb.sync_onbeat import sync_onbeat
    sync_onbeat()


def _sync_cogwork(args) -> None:
    from src.models.dancedb.sync_cogwork import sync_cogwork
    sync_cogwork()


def _sync_folketshus(args) -> None:
    from src.models.dancedb.sync_folketshus import sync_folketshus
    sync_folketshus()


def _sync_all(args) -> None:
    from src.models.dancedb.sync_all import sync_all
    from src.models.dancedb.sync_danslogen import get_month_year
    month, year = get_month_year(args.month, args.year)
    sync_all(
        month=month,
        year=year,
        limit=args.limit,
        only_scrape=args.only_scrape,
    )


def _scrape_bygdegardarna(args) -> None:
    from src.models.dancedb.venue_ops import scrape_bygdegardarna
    from datetime import date
    date_str = args.date or date.today().strftime("%Y-%m-%d")
    scrape_bygdegardarna(date_str)


def _scrape_dancedb_venues(args) -> None:
    from src.models.dancedb.venue_ops import scrape_dancedb_venues
    date_str = get_date_str(args.date)
    scrape_dancedb_venues(date_str)


def _match_bygdegardarna_venues(args) -> None:
    from src.models.dancedb.venue_ops import match_venues
    date_str = get_date_str(args.date)
    match_venues(date_str, skip_prompts=args.skip_prompts)


def _scrape_folketshus(args) -> None:
    from src.models.folketshus.venue import run as scrape_folketshus
    scrape_folketshus(date_str=args.date)


def _scrape_wikidata_artists(args) -> None:
    from src.models.wikidata.operations import scrape_wikidata_artists
    date_str = get_date_str(args.date)
    scrape_wikidata_artists(date_str)


def _match_wikidata_artists(args) -> None:
    from src.models.wikidata.operations import match_wikidata_artists
    date_str = get_date_str(args.date)
    match_wikidata_artists(date_str)


def _sync_wikidata_artists(args) -> None:
    from src.models.wikidata.operations import sync_wikidata_artists
    date_str = get_date_str(args.date)
    sync_wikidata_artists(date_str, month=args.month, year=args.year)


def _find_duplicate_venues(args) -> None:
    from src.models.dancedb.client import DancedbClient
    from src.utils.distance import haversine_distance
    import config

    threshold_km = args.threshold
    print(f"\n=== Finding duplicate venues (within {threshold_km*1000:.0f}m) ===")

    client = DancedbClient()
    venues = client.fetch_venues_from_dancedb()

    venues_with_coords = []
    seen_qids = set()
    for v in venues:
        if v["qid"] in seen_qids:
            continue
        p4 = v.get("p4", "")
        if p4:
            try:
                coords = p4.replace("Point(", "").replace(")", "").split(" ")
                lng, lat = float(coords[0]), float(coords[1])
                venues_with_coords.append({
                    "qid": v["qid"],
                    "label": v["label"],
                    "lat": lat,
                    "lng": lng,
                })
                seen_qids.add(v["qid"])
            except Exception:
                continue

    print(f"Found {len(venues_with_coords)} venues with unique coordinates")

    duplicates = []
    for i, v1 in enumerate(venues_with_coords):
        for v2 in venues_with_coords[i+1:]:
            dist = haversine_distance(v1["lat"], v1["lng"], v2["lat"], v2["lng"])
            if dist <= threshold_km:
                duplicates.append({
                    "v1": v1,
                    "v2": v2,
                    "distance_km": dist,
                })

    duplicates.sort(key=lambda x: x["distance_km"])

    print(f"Found {len(duplicates)} potential duplicate pairs:\n")
    for i, dup in enumerate(duplicates, 1):
        v1, v2 = dup["v1"], dup["v2"]
        dist_m = dup["distance_km"] * 1000
        url1 = f"https://dance.wikibase.cloud/wiki/Item:{v1['qid']}"
        url2 = f"https://dance.wikibase.cloud/wiki/Item:{v2['qid']}"
        print(f"{i}. {v1['label']} ({v1['qid']}) <-> {v2['label']} ({v2['qid']})")
        print(f"   Distance: {dist_m:.0f}m")
        print(f"   {url1}")
        print(f"   {url2}")
        print()


def _merge_duplicate_venues(args) -> None:
    from src.models.dancedb.client import DancedbClient
    from src.utils.distance import haversine_distance
    from src.utils.fuzzy import normalize_for_fuzzy
    from rapidfuzz import fuzz
    import questionary
    import config

    threshold_km = args.threshold
    fuzzy_threshold = args.fuzzy

    print(f"\n=== Finding merge candidates (distance <{threshold_km*1000:.0f}m, fuzzy >={fuzzy_threshold}%) ===")

    client = DancedbClient()
    venues = client.fetch_venues_from_dancedb()

    venues_with_coords = []
    for v in venues:
        p4 = v.get("p4", "")
        if p4:
            try:
                coords = p4.replace("Point(", "").replace(")", "").split(" ")
                lng, lat = float(coords[0]), float(coords[1])
                venues_with_coords.append({
                    "qid": v["qid"],
                    "label": v["label"],
                    "aliases": v.get("aliases", []),
                    "lat": lat,
                    "lng": lng,
                })
            except Exception:
                continue

    print(f"Found {len(venues_with_coords)} venues with coordinates")

    candidates = []
    for i, v1 in enumerate(venues_with_coords):
        for v2 in venues_with_coords[i+1:]:
            dist = haversine_distance(v1["lat"], v1["lng"], v2["lat"], v2["lng"])
            if dist > threshold_km:
                continue

            v1_names = [v1["label"]] + v1.get("aliases", [])
            v2_names = [v2["label"]] + v2.get("aliases", [])

            best_score = 0
            for n1 in v1_names:
                for n2 in v2_names:
                    n1_norm = normalize_for_fuzzy(n1.lower(), [])
                    n2_norm = normalize_for_fuzzy(n2.lower(), [])
                    score = fuzz.ratio(n1_norm, n2_norm)
                    best_score = max(best_score, score)

            if best_score >= fuzzy_threshold:
                candidates.append({
                    "v1": v1,
                    "v2": v2,
                    "distance_km": dist,
                    "fuzzy_score": best_score,
                })

    candidates.sort(key=lambda x: (x["fuzzy_score"], -x["distance_km"]))

    print(f"Found {len(candidates)} merge candidates\n")

    for i, c in enumerate(candidates, 1):
        v1, v2 = c["v1"], c["v2"]
        dist_m = c["distance_km"] * 1000
        url1 = f"https://dance.wikibase.cloud/wiki/Item:{v1['qid']}"
        url2 = f"https://dance.wikibase.cloud/wiki/Item:{v2['qid']}"

        print(f"{i}. {v1['label']} ({v1['qid']}) <-> {v2['label']} ({v2['qid']})")
        print(f"   Distance: {dist_m:.0f}m | Fuzzy: {c['fuzzy_score']:.0f}%")
        print(f"   {url1}")
        print(f"   {url2}")

        qid1_num = int(v1["qid"].replace("Q", ""))
        qid2_num = int(v2["qid"].replace("Q", ""))
        from_qid = f"Q{max(qid1_num, qid2_num)}"
        to_qid = f"Q{min(qid1_num, qid2_num)}"

        choice = questionary.select(
            f"Merge '{from_qid}' into '{to_qid}'?",
            choices=[f"Merge {from_qid} -> {to_qid} (Recommended)", "Skip", "Skip all", "Abort"]
        ).ask()

        if choice == "Abort":
            print("Aborting...")
            break
        elif choice == "Skip all":
            print("Skipping remaining candidates.")
            break
        elif choice == "Skip":
            continue
        elif "Merge" in choice:
            try:
                from wikibaseintegrator.wbi_helpers import merge_items, edit_entity
                merge_items(from_id=from_qid, to_id=to_qid, login=client.login, is_bot=True, ignore_conflicts=["description"])
                print(f"  Merged {from_qid} into {to_qid}")

                edit_entity(
                    entity_id=from_qid,
                    data={
                        "labels": {"remove": ""},
                        "descriptions": {"remove": ""},
                        "aliases": {"remove": ""},
                    },
                    login=client.login,
                    bot=True,
                )
                print(f"  Cleared {from_qid}")

                session = client.login.get_session()
                api_url = client.login.mediawiki_api_url
                data = {
                    "action": "wbcreateredirect",
                    "from": from_qid,
                    "to": to_qid,
                    "token": client.login.get_edit_token(),
                    "bot": "1",
                }
                response = session.post(api_url, data=data)
                result = response.json()
                if "error" in result:
                    print(f"  Redirect error: {result['error']['info']}")
                else:
                    print(f"  Created redirect: {from_qid} -> {to_qid}")
            except Exception as e:
                print(f"  ERROR: {e}")
        print()
