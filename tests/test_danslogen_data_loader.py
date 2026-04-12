import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.models.danslogen.data_loader import DanslogenDataLoader


class TestDanslogenDataLoaderLoadBygdegardarna:
    @patch('src.models.danslogen.data_loader.Path.read_text')
    def test_loads_bygdegardarna_venues(self, mock_read_text):
        mock_data = [
            {"title": "Test Venue 1", "position": {"lat": 59.0, "lng": 18.0}},
            {"title": "Test Venue 2", "position": {"lat": 60.0, "lng": 19.0}},
        ]
        mock_read_text.return_value = json.dumps(mock_data)

        loader = DanslogenDataLoader()
        result = loader.load_bygdegardarna_venues("2026-04-12")

        assert len(result) == 2
        assert "test venue 1" in result
        assert result["test venue 1"]["position"]["lat"] == 59.0

    @patch('src.models.danslogen.data_loader.Path.exists')
    def test_returns_empty_when_file_missing(self, mock_exists):
        mock_exists.return_value = False

        loader = DanslogenDataLoader()
        result = loader.load_bygdegardarna_venues("2026-04-12")

        assert result == {}


class TestDanslogenDataLoaderLoadDancedb:
    @patch('src.models.danslogen.data_loader.Path.read_text')
    def test_loads_dancedb_venues(self, mock_read_text):
        mock_data = {
            "Q123": {"label": "Test Hall", "lat": 59.0, "lng": 18.0},
            "Q456": {"label": "Test Barn", "lat": 60.0, "lng": 19.0},
        }
        mock_read_text.return_value = json.dumps(mock_data)

        loader = DanslogenDataLoader()
        result = loader.load_dancedb_venues("2026-04-12")

        assert len(result) == 2
        assert "Q123" in result
        assert result["Q123"]["label"] == "Test Hall"

    @patch('src.models.danslogen.data_loader.Path.exists')
    def test_returns_empty_when_file_missing(self, mock_exists):
        mock_exists.return_value = False

        loader = DanslogenDataLoader()
        result = loader.load_dancedb_venues("2026-04-12")

        assert result == {}


class TestDanslogenDataLoaderLoadRows:
    def test_returns_empty_when_file_missing(self):
        loader = DanslogenDataLoader()
        result = loader.load_rows("data/nonexistent.json")

        assert result == []