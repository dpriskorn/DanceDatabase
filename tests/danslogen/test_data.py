import json
import unittest.mock
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.models.danslogen.data import DataNotFoundError, _reset_instance, get_today_str, load_band_map, load_venue_map


class TestGetTodayStr:
    def test_returns_today_formatted(self):
        with patch("src.models.danslogen.data.date") as mock_date:
            mock_date.today.return_value = date(2026, 4, 15)
            result = get_today_str()
            assert result == "2026-04-15"


class TestLoadBandMap:
    @patch("config.dancedb_artists_dir")
    def test_raises_error_when_directory_missing(self, mock_dir):
        mock_dir.exists.return_value = False
        with pytest.raises(DataNotFoundError) as exc_info:
            load_band_map()
        assert "DanceDB artists directory not found" in str(exc_info.value)

    @patch("config.dancedb_artists_dir")
    def test_raises_error_when_file_missing(self, mock_dir):
        mock_dir.exists.return_value = True
        mock_dir.__truediv__ = lambda self, x: MagicMock(exists=lambda: False)
        with pytest.raises(DataNotFoundError) as exc_info:
            load_band_map()
        assert "Artists data file not found for today" in str(exc_info.value)

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.read_text")
    @patch("src.models.danslogen.data.get_today_str")
    @patch("config.dancedb_artists_dir")
    def test_loads_band_map_successfully(self, mock_dir, mock_today, mock_read, mock_exists):
        _reset_instance()
        artists_content = [
            {"qid": "Q123", "label": "Test Band", "aliases": ["Test", "Band"]},
            {"qid": "Q456", "label": "Another Band", "aliases": []},
        ]
        mock_today.return_value = "2026-04-15"
        mock_dir.__truediv__.return_value.exists.return_value = True
        mock_dir.__truediv__.return_value.read_text.return_value = json.dumps(artists_content)

        result = load_band_map()

        assert result["test band"] == "Q123"
        assert result["another band"] == "Q456"
        assert result["test"] == "Q123"
        assert result["band"] == "Q123"

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.read_text")
    @patch("src.models.danslogen.data.get_today_str")
    @patch("config.dancedb_artists_dir")
    def test_handles_missing_qid_or_label(self, mock_dir, mock_today, mock_read, mock_exists):
        _reset_instance()
        artists_content = [
            {"label": "No QID"},
            {"qid": "Q123"},
            {},
        ]
        mock_today.return_value = "2026-04-15"
        mock_dir.__truediv__.return_value.exists.return_value = True
        mock_dir.__truediv__.return_value.read_text.return_value = json.dumps(artists_content)

        result = load_band_map()
        assert result == {}


class TestLoadVenueMap:
    @patch("config.dancedb_venues_dir")
    def test_raises_error_when_directory_missing(self, mock_dir):
        mock_dir.exists.return_value = False
        with pytest.raises(DataNotFoundError) as exc_info:
            load_venue_map()
        assert "DanceDB venues directory not found" in str(exc_info.value)

    @patch("config.dancedb_venues_dir")
    def test_raises_error_when_file_missing(self, mock_dir):
        mock_dir.exists.return_value = True
        mock_dir.__truediv__ = lambda self, x: MagicMock(exists=lambda: False)
        with pytest.raises(DataNotFoundError) as exc_info:
            load_venue_map()
        assert "Venues data file not found for today" in str(exc_info.value)

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.read_text")
    @patch("src.models.danslogen.data.get_today_str")
    @patch("config.dancedb_venues_dir")
    def test_loads_venue_map_successfully(self, mock_dir, mock_today, mock_read, mock_exists):
        _reset_instance()
        venues_content = {
            "Q123": {"label": "Test Venue", "aliases": ["Venue", "Test"]},
            "Q456": {"label": "Another Venue", "aliases": []},
        }
        mock_today.return_value = "2026-04-15"
        mock_dir.__truediv__.return_value.exists.return_value = True
        mock_dir.__truediv__.return_value.read_text.return_value = json.dumps(venues_content)

        result = load_venue_map()

        assert result["test venue"] == "Q123"
        assert result["another venue"] == "Q456"
        assert result["venue"] == "Q123"
        assert result["test"] == "Q123"

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.read_text")
    @patch("src.models.danslogen.data.get_today_str")
    @patch("config.dancedb_venues_dir")
    def test_handles_missing_label(self, mock_dir, mock_today, mock_read, mock_exists):
        _reset_instance()
        venues_content = {
            "Q123": {},
            "Q456": {"label": ""},
        }
        mock_today.return_value = "2026-04-15"
        mock_dir.__truediv__.return_value.exists.return_value = True
        mock_dir.__truediv__.return_value.read_text.return_value = json.dumps(venues_content)

        result = load_venue_map()
        assert result == {}
