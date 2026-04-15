import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.models.danslogen.data import (
    DataNotFoundError,
    load_band_map,
    load_venue_map,
    get_today_str,
    DANCEDB_ARTISTS_DIR,
    DANCEDB_VENUES_DIR,
    _reset_instance,
)


class TestGetTodayStr:
    def test_returns_today_formatted(self):
        result = get_today_str()
        assert result == "2026-04-15"


class TestLoadBandMap:
    @patch('src.models.danslogen.data.DANCEDB_ARTISTS_DIR')
    def test_raises_error_when_directory_missing(self, mock_dir):
        mock_dir.exists.return_value = False
        with pytest.raises(DataNotFoundError) as exc_info:
            load_band_map()
        assert "DanceDB artists directory not found" in str(exc_info.value)

    @patch('src.models.danslogen.data.DANCEDB_ARTISTS_DIR')
    def test_raises_error_when_file_missing(self, mock_dir):
        mock_dir.exists.return_value = True
        mock_dir.__truediv__ = lambda self, x: MagicMock(exists=lambda: False)
        with pytest.raises(DataNotFoundError) as exc_info:
            load_band_map()
        assert "Artists data file not found for today" in str(exc_info.value)

    @patch('src.models.danslogen.data.DANCEDB_ARTISTS_DIR')
    def test_loads_band_map_successfully(self, mock_dir):
        _reset_instance()
        artists_file = MagicMock()
        artists_content = [
            {"qid": "Q123", "label": "Test Band", "aliases": ["Test", "Band"]},
            {"qid": "Q456", "label": "Another Band", "aliases": []},
        ]
        artists_file.read_text.return_value = json.dumps(artists_content)
        artists_file.name = "2026-04-15.json"
        
        def mock_truediv(self, other):
            return artists_file if other == "2026-04-15.json" else MagicMock()
        
        mock_dir.exists.return_value = True
        mock_dir.__truediv__ = mock_truediv
        
        result = load_band_map()
        
        assert result["test band"] == "Q123"
        assert result["another band"] == "Q456"
        assert result["test"] == "Q123"
        assert result["band"] == "Q123"

    @patch('src.models.danslogen.data.DANCEDB_ARTISTS_DIR')
    def test_handles_missing_qid_or_label(self, mock_dir):
        _reset_instance()
        artists_file = MagicMock()
        artists_content = [
            {"label": "No QID"},
            {"qid": "Q123"},
            {},
        ]
        artists_file.read_text.return_value = json.dumps(artists_content)
        artists_file.name = "2026-04-15.json"
        
        def mock_truediv(self, other):
            return artists_file if other == "2026-04-15.json" else MagicMock()
        
        mock_dir.exists.return_value = True
        mock_dir.__truediv__ = mock_truediv
        
        result = load_band_map()
        assert result == {}


class TestLoadVenueMap:
    @patch('src.models.danslogen.data.DANCEDB_VENUES_DIR')
    def test_raises_error_when_directory_missing(self, mock_dir):
        mock_dir.exists.return_value = False
        with pytest.raises(DataNotFoundError) as exc_info:
            load_venue_map()
        assert "DanceDB venues directory not found" in str(exc_info.value)

    @patch('src.models.danslogen.data.DANCEDB_VENUES_DIR')
    def test_raises_error_when_file_missing(self, mock_dir):
        mock_dir.exists.return_value = True
        mock_dir.__truediv__ = lambda self, x: MagicMock(exists=lambda: False)
        with pytest.raises(DataNotFoundError) as exc_info:
            load_venue_map()
        assert "Venues data file not found for today" in str(exc_info.value)

    @patch('src.models.danslogen.data.DANCEDB_VENUES_DIR')
    def test_loads_venue_map_successfully(self, mock_dir):
        _reset_instance()
        venues_file = MagicMock()
        venues_content = {
            "Q123": {"label": "Test Venue", "aliases": ["Venue", "Test"]},
            "Q456": {"label": "Another Venue", "aliases": []},
        }
        venues_file.read_text.return_value = json.dumps(venues_content)
        venues_file.name = "2026-04-15.json"
        
        def mock_truediv(self, other):
            return venues_file if other == "2026-04-15.json" else MagicMock()
        
        mock_dir.exists.return_value = True
        mock_dir.__truediv__ = mock_truediv
        
        result = load_venue_map()
        
        assert result["test venue"] == "Q123"
        assert result["another venue"] == "Q456"
        assert result["venue"] == "Q123"
        assert result["test"] == "Q123"

    @patch('src.models.danslogen.data.DANCEDB_VENUES_DIR')
    def test_handles_missing_label(self, mock_dir):
        _reset_instance()
        venues_file = MagicMock()
        venues_content = {
            "Q123": {},
            "Q456": {"label": ""},
        }
        venues_file.read_text.return_value = json.dumps(venues_content)
        venues_file.name = "2026-04-15.json"
        
        def mock_truediv(self, other):
            return venues_file if other == "2026-04-15.json" else MagicMock()
        
        mock_dir.exists.return_value = True
        mock_dir.__truediv__ = mock_truediv
        
        result = load_venue_map()
        assert result == {}
