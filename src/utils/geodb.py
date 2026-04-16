import json
import math
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import config
from src.utils.distance import haversine_distance


def get_db_path() -> Path:
    return config.data_dir / "venues.db"


def init_db() -> sqlite3.Connection:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS venues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            source TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            external_id TEXT,
            qid TEXT,
            address TEXT,
            city TEXT,
            phone TEXT,
            email TEXT,
            permalink TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(source, external_id)
        )
    """)
    
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS venues_geom USING rtree(
            id,
            min_lat, max_lat,
            min_lng, max_lng
        )
    """)
    
    conn.commit()
    return conn


def ensure_db():
    db_path = get_db_path()
    if not db_path.exists():
        return init_db()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _bbox_from_point(lat: float, lng: float, threshold_km: float) -> tuple:
    lat_delta = threshold_km / 111.0
    cos_lat = math.cos(math.radians(lat)) if abs(lat) > 0.001 else 1.0
    lng_delta = threshold_km / (111.0 * cos_lat)
    return (lat - lat_delta, lat + lat_delta, lng - lng_delta, lng + lng_delta)


def load_bygdegardarna():
    conn = ensure_db()
    
    enriched_dir = config.bygdegardarna_dir / "enriched"
    raw_dir = config.bygdegardarna_dir
    
    files_to_check = []
    if enriched_dir.exists():
        files_to_check.extend(sorted(enriched_dir.glob("*.json"), reverse=True))
    if raw_dir.exists():
        files_to_check.extend(sorted(raw_dir.glob("*.json"), reverse=True))
    
    seen = set()
    count = 0
    
    for byg_file in files_to_check:
        data = json.loads(byg_file.read_text())
        for v in data:
            name = v.get("title", "").strip()
            meta = v.get("meta", {})
            position = v.get("position", {})
            
            if not name:
                continue
            
            lat = position.get("lat")
            lng = position.get("lng")
            if not lat or not lng:
                continue
            
            permalink = meta.get("permalink", "")
            if not permalink:
                continue
            parts = permalink.rstrip("/").split("/")
            external_id = v.get("external_id") or (parts[-1] if parts else None)
            if not external_id:
                continue
            
            key = ("bygdegardarna", external_id)
            if key in seen:
                continue
            seen.add(key)
            
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO venues 
                    (name, source, lat, lng, external_id, address, city, phone, email, permalink, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    name, "bygdegardarna", lat, lng, external_id,
                    meta.get("address", ""), meta.get("city", ""),
                    meta.get("phone", ""), meta.get("email", ""),
                    meta.get("permalink", ""),
                    datetime.now().isoformat()
                ))
                count += 1
            except sqlite3.IntegrityError:
                pass
    
    conn.commit()
    conn.close()
    print(f"Loaded {count} bygdegardarna venues into geodb")


def load_folketshus():
    conn = ensure_db()
    
    enriched_dir = config.data_dir / "folketshus" / "enriched"
    
    if not enriched_dir.exists():
        print("No folketshus enriched directory found")
        return
    
    files = sorted(enriched_dir.glob("*.json"), reverse=True)
    
    seen = set()
    count = 0
    
    for folk_file in files:
        data = json.loads(folk_file.read_text())
        for v in data:
            name = v.get("name", "").strip()
            external_id = v.get("external_id", "")
            
            if not name:
                continue
            
            lat = v.get("lat")
            lng = v.get("lng")
            if not lat or not lng:
                continue
            
            if not external_id:
                continue
            
            key = ("folketshus", external_id)
            if key in seen:
                continue
            seen.add(key)
            
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO venues 
                    (name, source, lat, lng, external_id, qid, address, city, permalink, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    name, "folketshus", lat, lng, external_id, v.get("qid", ""),
                    v.get("address", ""), v.get("region", ""),
                    v.get("url", ""),
                    datetime.now().isoformat()
                ))
                count += 1
            except sqlite3.IntegrityError:
                pass
    
    conn.commit()
    conn.close()
    print(f"Loaded {count} folketshus venues into geodb")


def find_nearby(lat: float, lng: float, threshold_km: float = 0.1, limit: int = 10) -> list:
    conn = ensure_db()
    
    lat_min, lat_max, lng_min, lng_max = _bbox_from_point(lat, lng, threshold_km)
    
    cursor = conn.execute("""
        SELECT id, name, source, lat, lng, external_id, qid, address, city, phone, email, permalink
        FROM venues
        WHERE lat BETWEEN ? AND ? AND lng BETWEEN ? AND ?
    """, (lat_min, lat_max, lng_min, lng_max))
    
    results = []
    for row in cursor:
        dist = haversine_distance(lat, lng, row["lat"], row["lng"])
        if dist <= threshold_km:
            results.append({
                "id": row["id"],
                "name": row["name"],
                "source": row["source"],
                "lat": row["lat"],
                "lng": row["lng"],
                "external_id": row["external_id"],
                "qid": row["qid"],
                "address": row["address"],
                "city": row["city"],
                "phone": row["phone"],
                "email": row["email"],
                "permalink": row["permalink"],
                "distance_km": dist,
            })
    
    results.sort(key=lambda x: x["distance_km"])
    conn.close()
    return results[:limit]


def find_nearby_by_name(name: str, threshold_km: float = 0.1) -> list:
    conn = ensure_db()
    
    cursor = conn.execute("""
        SELECT id, name, source, lat, lng, external_id, qid, address, city, phone, email, permalink
        FROM venues
        WHERE LOWER(name) LIKE LOWER(?)
    """, (f"%{name}%",))
    
    results = []
    for row in cursor:
        lat, lng = row["lat"], row["lng"]
        dist = haversine_distance(0, 0, 0, 0)
        
        results.append({
            "id": row["id"],
            "name": row["name"],
            "source": row["source"],
            "lat": lat,
            "lng": lng,
            "external_id": row["external_id"],
            "qid": row["qid"],
            "address": row["address"],
            "city": row["city"],
            "phone": row["phone"],
            "email": row["email"],
            "permalink": row["permalink"],
            "distance_km": dist,
        })
    
    conn.close()
    return results


def update_qid(external_id: str, source: str, qid: str):
    conn = ensure_db()
    conn.execute("""
        UPDATE venues SET qid = ? WHERE source = ? AND external_id = ?
    """, (qid, source, external_id))
    conn.commit()
    conn.close()


def get_stats() -> dict:
    conn = ensure_db()
    cursor = conn.execute("""
        SELECT source, COUNT(*) as count FROM venues GROUP BY source
    """)
    stats = {row["source"]: row["count"] for row in cursor}
    conn.close()
    return stats


def load_dancedb():
    from src.models.dancedb.client import DancedbClient
    
    conn = ensure_db()
    
    print("Fetching venues from DanceDB...")
    client = DancedbClient()
    venues = client.fetch_venues_from_dancedb()
    print(f"Found {len(venues)} venues on DanceDB")
    
    count = 0
    for v in venues:
        name = v.get("label", "").strip()
        qid = v.get("qid", "")
        p4 = v.get("p4", "")
        
        lat, lng = None, None
        if p4:
            try:
                coords = p4.replace("Point(", "").replace(")", "").split(" ")
                lng, lat = float(coords[0]), float(coords[1])
            except Exception:
                pass
        
        if not name or not qid or not lat or not lng:
            continue
        
        try:
            conn.execute("""
                INSERT OR REPLACE INTO venues 
                (name, source, lat, lng, qid, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, "dancedb", lat, lng, qid, datetime.now().isoformat()))
            count += 1
        except sqlite3.IntegrityError:
            pass
    
    conn.commit()
    conn.close()
    print(f"Loaded {count} dancedb venues into geodb")


def rebuild():
    import os
    db_path = get_db_path()
    if db_path.exists():
        os.remove(db_path)
    init_db()
    load_bygdegardarna()
    load_folketshus()
    load_dancedb()
    print(f"Geodb rebuilt. Stats: {get_stats()}")


def get_ship_coordinates(venue_name: str) -> Optional[dict]:
    """Check if venue name matches ship patterns and return default coordinates."""
    name_lower = venue_name.lower()
    for pattern, coords in config.SHIP_COORDINATES.items():
        if pattern in name_lower:
            return {"lat": coords["lat"], "lng": coords["lng"]}
    return None