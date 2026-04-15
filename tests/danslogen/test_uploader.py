import pytest
from unittest.mock import MagicMock, patch

from src.models.danslogen.uploader import DanslogenUploader


class TestDanslogenUploaderInit:
    def test_sets_defaults(self):
        uploader = DanslogenUploader(
            filename="test.json",
            date_str="2026-04-12",
            month="april",
        )

        assert uploader.filename == "test.json"
        assert uploader.date_str == "2026-04-12"
        assert uploader.month == "april"
        assert uploader.client is None

    def test_limit_stored(self):
        uploader = DanslogenUploader(
            filename="test.json",
            limit=10,
        )

        assert uploader.limit == 10


class TestDanslogenUploaderRun:
    @patch('src.models.danslogen.uploader.DanslogenData')
    def test_loads_venue_data(self, mock_loader_class):
        mock_loader = MagicMock()
        mock_loader.load_bygdegardarna_venues.return_value = {"test": {"lat": 1.0}}
        mock_loader.load_dancedb_venues.return_value = {"Q1": {"label": "Test"}}
        mock_loader.load_rows.return_value = []
        mock_loader_class.return_value = mock_loader

        uploader = DanslogenUploader(filename="test.json", date_str="2026-04-12")
        uploader.run(dry_run=True)

        mock_loader.load_bygdegardarna_venues.assert_called_once_with("2026-04-12")
        mock_loader.load_dancedb_venues.assert_called_once_with("2026-04-12")

    @patch('src.models.danslogen.uploader.DanslogenData')
    def test_returns_counts_on_empty(self, mock_loader_class):
        mock_loader = MagicMock()
        mock_loader.load_bygdegardarna_venues.return_value = {}
        mock_loader.load_dancedb_venues.return_value = {}
        mock_loader.load_rows.return_value = []
        mock_loader_class.return_value = mock_loader

        uploader = DanslogenUploader(filename="test.json")
        processed, events, skipped = uploader.run(dry_run=True)

        assert processed == 0
        assert events == 0
        assert skipped == 0


class TestDanslogenUploaderWithRows:
    def test_returns_counts_on_empty(self):
        uploader = DanslogenUploader(filename="nonexistent.json")
        processed, events, skipped = uploader.run(dry_run=True)

        assert processed == 0
        assert events == 0
        assert skipped == 0