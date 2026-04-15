import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.models.onbeat.venue_resolver import VenueResolver


class TestVenueResolverInit:
    def test_initializes_with_default_data_dir(self):
        resolver = VenueResolver()
        assert resolver.data_dir == Path("data")

    def test_initializes_with_custom_data_dir(self):
        resolver = VenueResolver(data_dir="/custom/path")
        assert resolver.data_dir == Path("/custom/path")

    def test_initializes_with_empty_caches(self):
        resolver = VenueResolver()
        assert resolver._dancedb_venues == {}
        assert resolver._folketshus_venues == {}
        assert resolver._bygdegardarna_venues == []


class TestVenueResolverLoadDancedbVenues:
    @patch("src.models.onbeat.venue_resolver.Path.exists")
    @patch("src.models.onbeat.venue_resolver.Path.read_text")
    @patch("src.models.onbeat.venue_resolver.json.loads")
    def test_loads_cached_venues(self, mock_json_loads, mock_read_text, mock_exists):
        mock_exists.return_value = True
        mock_read_text.return_value = '{"Q123": {"label": "Test Venue", "aliases": []}}'
        mock_json_loads.return_value = {"Q123": {"label": "Test Venue", "aliases": []}}

        resolver = VenueResolver()
        result = resolver._load_dancedb_venues()

        assert result == {"Q123": {"label": "Test Venue", "aliases": []}}
        mock_json_loads.assert_called_once()

    @patch("src.models.onbeat.venue_resolver.Path.exists")
    def test_returns_empty_dict_when_file_missing(self, mock_exists):
        mock_exists.return_value = False

        resolver = VenueResolver()
        result = resolver._load_dancedb_venues()

        assert result == {}

    def test_caches_after_first_load(self):
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "read_text", return_value='{"Q123": {"label": "Test"}}'):
                resolver = VenueResolver()
                
                result1 = resolver._load_dancedb_venues()
                result2 = resolver._load_dancedb_venues()
                
                assert result1 is result2


class TestVenueResolverLoadFolketshusVenues:
    @patch("src.models.onbeat.venue_resolver.Path.exists")
    @patch("src.models.onbeat.venue_resolver.Path.read_text")
    @patch("src.models.onbeat.venue_resolver.json.loads")
    def test_loads_folketshus_venues(self, mock_json_loads, mock_read_text, mock_exists):
        mock_exists.return_value = True
        mock_read_text.return_value = '[{"name": "Folkets Hus", "qid": "Q456", "external_id": "FH123"}, {"name": "Another Venue", "qid": null}]'
        mock_json_loads.return_value = [
            {"name": "Folkets Hus", "qid": "Q456", "external_id": "FH123"},
            {"name": "Another Venue", "qid": None},
        ]

        resolver = VenueResolver()
        result = resolver._load_folketshus_venues()

        assert "folkets hus" in result
        assert result["folkets hus"]["qid"] == "Q456"
        assert result["folkets hus"]["external_id"] == "FH123"

    @patch("src.models.onbeat.venue_resolver.Path.exists")
    def test_skips_venues_without_qid(self, mock_exists):
        mock_exists.return_value = True
        mock_json_loads = [{"name": "No QID Venue", "qid": None}]
        
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "read_text", return_value=json.dumps(mock_json_loads)):
                resolver = VenueResolver()
                result = resolver._load_folketshus_venues()
                
                assert "no qid venue" not in result


class TestVenueResolverLoadBygdegardarnaVenues:
    @patch("src.models.onbeat.venue_resolver.Path.exists")
    @patch("src.models.onbeat.venue_resolver.Path.read_text")
    @patch("src.models.onbeat.venue_resolver.json.loads")
    def test_loads_bygdegardarna_venues(self, mock_json_loads, mock_read_text, mock_exists):
        mock_exists.return_value = True
        mock_read_text.return_value = '[{"title": "Bygdegarden 1", "meta": {"permalink": "abc"}}, {"title": "Bygdegarden 2"}]'
        mock_json_loads.return_value = [
            {"title": "Bygdegarden 1", "meta": {"permalink": "abc"}},
            {"title": "Bygdegarden 2"},
        ]

        resolver = VenueResolver()
        result = resolver._load_bygdegardarna_venues()

        assert len(result) == 2

    @patch("src.models.onbeat.venue_resolver.Path.exists")
    def test_returns_empty_list_when_file_missing(self, mock_exists):
        mock_exists.return_value = False

        resolver = VenueResolver()
        result = resolver._load_bygdegardarna_venues()

        assert result == []


class TestVenueResolverLookup:
    @patch.object(VenueResolver, "_load_dancedb_venues")
    @patch.object(VenueResolver, "_load_folketshus_venues")
    @patch.object(VenueResolver, "_load_bygdegardarna_venues")
    def test_returns_none_for_empty_venue_name(self, mock_byg, mock_folk, mock_dancedb):
        resolver = VenueResolver()
        qid, external_id = resolver.lookup("")
        
        assert qid is None
        assert external_id is None

    @patch.object(VenueResolver, "_load_dancedb_venues")
    @patch.object(VenueResolver, "_load_folketshus_venues")
    @patch.object(VenueResolver, "_load_bygdegardarna_venues")
    def test_finds_exact_match_in_dancedb(self, mock_byg, mock_folk, mock_dancedb):
        mock_dancedb.return_value = {"Q123": {"label": "Test Venue", "aliases": []}}

        resolver = VenueResolver()
        qid, external_id = resolver.lookup("Test Venue")

        assert qid == "Q123"
        assert external_id is None

    @patch.object(VenueResolver, "_load_dancedb_venues")
    @patch.object(VenueResolver, "_load_folketshus_venues")
    @patch.object(VenueResolver, "_load_bygdegardarna_venues")
    def test_finds_partial_match_in_dancedb(self, mock_byg, mock_folk, mock_dancedb):
        mock_dancedb.return_value = {"Q123": {"label": "Test Venue Hall", "aliases": []}}

        resolver = VenueResolver()
        qid, external_id = resolver.lookup("Test Venue")

        assert qid == "Q123"

    @patch.object(VenueResolver, "_load_dancedb_venues")
    @patch.object(VenueResolver, "_load_folketshus_venues")
    @patch.object(VenueResolver, "_load_bygdegardarna_venues")
    def test_finds_match_in_dancedb_aliases(self, mock_byg, mock_folk, mock_dancedb):
        mock_dancedb.return_value = {"Q123": {"label": "Main Venue", "aliases": ["alias venue", "test"]}}

        resolver = VenueResolver()
        qid, external_id = resolver.lookup("Test")

        assert qid == "Q123"

    @patch.object(VenueResolver, "_load_dancedb_venues")
    @patch.object(VenueResolver, "_load_folketshus_venues")
    @patch.object(VenueResolver, "_load_bygdegardarna_venues")
    def test_falls_back_to_folketshus(self, mock_byg, mock_folk, mock_dancedb):
        mock_dancedb.return_value = {}
        mock_folk.return_value = {"folkets hus": {"name": "Folkets Hus", "qid": "Q456", "external_id": "FH123"}}

        resolver = VenueResolver()
        qid, external_id = resolver.lookup("Folkets Hus")

        assert qid == "Q456"
        assert external_id == "FH123"

    @patch.object(VenueResolver, "_load_dancedb_venues")
    @patch.object(VenueResolver, "_load_folketshus_venues")
    @patch.object(VenueResolver, "_load_bygdegardarna_venues")
    def test_falls_back_to_bygdegardarna(self, mock_byg, mock_folk, mock_dancedb):
        mock_dancedb.return_value = {}
        mock_folk.return_value = {}
        mock_byg.return_value = [
            {"title": "Bygdegarden Test", "meta": {"permalink": "byg-test"}}
        ]

        resolver = VenueResolver()
        qid, external_id = resolver.lookup("Bygdegarden Test")

        assert qid is None
        assert external_id == "bygdegardarna:byg-test"

    @patch.object(VenueResolver, "_load_dancedb_venues")
    @patch.object(VenueResolver, "_load_folketshus_venues")
    @patch.object(VenueResolver, "_load_bygdegardarna_venues")
    def test_returns_none_when_not_found_anywhere(self, mock_byg, mock_folk, mock_dancedb):
        mock_dancedb.return_value = {}
        mock_folk.return_value = {}
        mock_byg.return_value = []

        resolver = VenueResolver()
        qid, external_id = resolver.lookup("Unknown Venue")

        assert qid is None
        assert external_id is None


class TestVenueResolverResolve:
    @patch.object(VenueResolver, "lookup")
    def test_returns_qid_and_external_id_when_found(self, mock_lookup):
        mock_lookup.return_value = ("Q123", "FH456")

        resolver = VenueResolver()
        qid, external_id = resolver.resolve("Test Venue")

        assert qid == "Q123"
        assert external_id == "FH456"

    @patch.object(VenueResolver, "lookup")
    def test_returns_empty_string_for_missing_qid(self, mock_lookup):
        mock_lookup.return_value = (None, None)

        resolver = VenueResolver()
        qid, external_id = resolver.resolve("Unknown Venue")

        assert qid == ""
        assert external_id is None

    @patch.object(VenueResolver, "lookup")
    def test_returns_empty_string_for_empty_venue_name(self, mock_lookup):
        mock_lookup.return_value = (None, None)

        resolver = VenueResolver()
        qid, external_id = resolver.resolve("")

        assert qid == ""
        assert external_id is None

    @patch.object(VenueResolver, "lookup")
    def test_preserves_external_id_when_qid_missing(self, mock_lookup):
        mock_lookup.return_value = (None, "bygdegardarna:test")

        resolver = VenueResolver()
        qid, external_id = resolver.resolve("Bygdegarden")

        assert qid == ""
        assert external_id == "bygdegardarna:test"
