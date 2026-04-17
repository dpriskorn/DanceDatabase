"""Data loading utilities for ensure_venues."""
import json
from pathlib import Path

from src.utils.google_maps import GoogleMaps
from src.utils.fuzzy import normalize_for_fuzzy


def load_bygdegardarna_venues():
    """Load enriched bygdegardarna venues."""
    bygdegardarna_dir = Path("data/bygdegardarna/enriched")
    venues = {}
    cities = {}
    names = []
    
    if bygdegardarna_dir.exists():
        files = sorted(bygdegardarna_dir.glob("*.json"), reverse=True)
        if files:
            data = json.loads(files[0].read_text())
            venues = {v["title"].lower(): v for v in data if v.get("qid")}
            names = list(venues.keys())
            for v in data:
                city = v.get("meta", {}).get("city", "").lower()
                if city and v.get("qid"):
                    position = v.get("position", {})
                    address = v.get("meta", {}).get("address", "")
                    gmaps = GoogleMaps(address=address, lat=position.get("lat"), lng=position.get("lng"))
                    v["gmaps_url"] = gmaps.url
                    cities[city] = v
    
    print(f"Loaded {len(venues)} bygdegardarna venues ({len(cities)} cities) for auto-match")
    return venues, names, cities


def load_folketshus_venues():
    """Load folketshus venues from enriched and unmatched directories."""
    folketshus_dir = Path("data/folketshus")
    venues = {}
    names = []
    
    for subdir in ["enriched", "unmatched"]:
        subdir_path = folketshus_dir / subdir
        if subdir_path.exists():
            files = sorted(subdir_path.glob("*.json"), reverse=True)
            if files:
                data = json.loads(files[0].read_text())
                for v in data:
                    v["source_dir"] = subdir
                    address = v.get("address", "")
                    lat = v.get("lat")
                    lng = v.get("lng")
                    gmaps = GoogleMaps(address=address, lat=lat, lng=lng)
                    v["gmaps_url"] = gmaps.url
                    name_lower = v["name"].lower()
                    if name_lower not in venues:
                        venues[name_lower] = v
                print(f"Loaded {len(data)} folketshus venues from {subdir}/")
    
    names = list(venues.keys())
    print(f"Loaded {len(venues)} total folketshus venues for auto-match")
    return venues, names


def load_bygdegardarna_addresses():
    """Load bygdegardarna venues for address matching."""
    addresses = {}
    seen = set()
    
    for subdir in ["enriched", ""]:
        dir_path = Path(f"data/bygdegardarna/{subdir}" if subdir else "data/bygdegardarna")
        if dir_path.exists():
            files = sorted(dir_path.glob("*.json"), reverse=True)
            for byg_file in files:
                data = json.loads(byg_file.read_text())
                for v in data:
                    title = v.get("title", "").lower()
                    meta = v.get("meta", {})
                    address = meta.get("address", "").lower()
                    position = v.get("position", {})
                    if title and address and position.get("lat") and address not in seen:
                        seen.add(address)
                        qid = v.get("qid", "")
                        gmaps = GoogleMaps(address=address, lat=position["lat"], lng=position["lng"])
                        gmaps_url = gmaps.url
                        permalink = meta.get("permalink", "")
                        if qid:
                            addresses[title] = {"qid": qid, "lat": position["lat"], "lng": position["lng"], "address": address, "gmaps_url": gmaps_url, "permalink": permalink}
                        addresses[address] = {"lat": position["lat"], "lng": position["lng"], "address": address, "qid": qid, "gmaps_url": gmaps_url, "permalink": permalink}
    
    print(f"Loaded {len(addresses)} bygdegardarna addresses for address matching")
    return addresses