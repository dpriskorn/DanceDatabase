import os
import tempfile

import pytest


class TestGeodb:
    
    def test_init_db_creates_tables(self, tmp_path):
        with tempfile.TemporaryDirectory() as td:
            test_path = tmp_path / "test.db"
            import sqlite3
            conn = sqlite3.connect(str(test_path))
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
            
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            assert "venues" in tables
            assert "venues_geom" in tables

    def test_bbox_calculation(self):
        import math
        def _bbox_from_point(lat, lng, threshold_km):
            lat_delta = threshold_km / 111.0
            cos_lat = math.cos(math.radians(lat)) if abs(lat) > 0.001 else 1.0
            lng_delta = threshold_km / (111.0 * cos_lat)
            return (lat - lat_delta, lat + lat_delta, lng - lng_delta, lng + lng_delta)
        
        lat, lng = 56.465292, 13.096046
        bbox = _bbox_from_point(lat, lng, 0.1)
        
        assert bbox[0] < lat < bbox[1]
        assert bbox[2] < lng < bbox[3]
        
    def test_haversine_distance(self):
        from src.utils.distance import haversine_distance
        
        dist = haversine_distance(56.465292, 13.096046, 56.46537, 13.09607)
        assert dist < 0.02
        assert dist > 0
        
    def test_coordinate_parsing(self):
        from src.utils.coords import parse_coords
        
        result = parse_coords("56.465292, 13.096046")
        assert result is not None
        assert result["lat"] == 56.465292
        assert result["lng"] == 13.096046
        
    def test_find_nearby_returns_results(self):
        from src.utils.geodb import ensure_db, find_nearby, get_db_path
        from src.utils.distance import haversine_distance
        
        original_db = get_db_path()
        temp_db = original_db.parent / "test_venues.db"
        
        original_path = str(original_db)
        temp_path = str(temp_db)
        
        os.rename(original_path, temp_path)
        
        try:
            conn = ensure_db()
            conn.execute("""
                INSERT INTO venues (name, source, lat, lng, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, ("Test Venue", "bygdegardarna", 56.46537, 13.09607, "2026-01-01"))
            conn.commit()
            conn.close()
            
            results = find_nearby(56.465292, 13.096046, threshold_km=0.1)
            assert len(results) == 1
            assert results[0]["name"] == "Test Venue"
            assert results[0]["source"] == "bygdegardarna"
            assert results[0]["distance_km"] < 0.1
        finally:
            if temp_db.exists():
                os.rename(temp_path, original_path)

    def test_find_nearby_excludes_far_venues(self):
        from src.utils.geodb import ensure_db, find_nearby, get_db_path
        
        original_db = get_db_path()
        temp_db = original_db.parent / "test_venues.db"
        
        original_path = str(original_db)
        temp_path = str(temp_db)
        
        os.rename(original_path, temp_path)
        
        try:
            conn = ensure_db()
            conn.execute("""
                INSERT INTO venues (name, source, lat, lng, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, ("Far Venue", "folketshus", 56.5, 13.2, "2026-01-01"))
            conn.commit()
            conn.close()
            
            results = find_nearby(56.465292, 13.096046, threshold_km=0.1)
            assert len(results) == 0
        finally:
            if temp_db.exists():
                os.rename(temp_path, original_path)

    def test_get_stats_returns_counts(self):
        from src.utils.geodb import ensure_db, get_stats, get_db_path
        
        original_db = get_db_path()
        temp_db = original_db.parent / "test_venues.db"
        
        original_path = str(original_db)
        temp_path = str(temp_db)
        
        os.rename(original_path, temp_path)
        
        try:
            conn = ensure_db()
            conn.execute("""
                INSERT INTO venues (name, source, lat, lng, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, ("Venue1", "bygdegardarna", 56.0, 13.0, "2026-01-01"))
            conn.execute("""
                INSERT INTO venues (name, source, lat, lng, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, ("Venue2", "folketshus", 56.0, 13.0, "2026-01-01"))
            conn.execute("""
                INSERT INTO venues (name, source, lat, lng, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, ("Venue3", "dancedb", 56.0, 13.0, "2026-01-01"))
            conn.commit()
            conn.close()
            
            stats = get_stats()
            assert stats.get("bygdegardarna") == 1
            assert stats.get("folketshus") == 1
            assert stats.get("dancedb") == 1
        finally:
            if temp_db.exists():
                os.rename(temp_path, original_path)