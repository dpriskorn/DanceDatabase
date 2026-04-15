import pytest
from unittest.mock import MagicMock, patch

from src.models.danslogen.venue_matcher import VenueMatcher


class TestVenueMatcherFindInBygdegardarna:
    def test_finds_exact_match_with_qid(self):
        byg_venues = {
            "test venue": {"qid": "Q456", "title": "Test Venue", "position": {"lat": 59.0, "lng": 18.0}},
        }
        matcher = VenueMatcher(byg_venues=byg_venues)
        result = matcher._find_in_bygdegardarna("Test Venue")

        assert result == "Q456"

    def test_returns_none_for_no_byg_venues(self):
        matcher = VenueMatcher(byg_venues=None)
        result = matcher._find_in_bygdegardarna("Test Venue")

        assert result is None


class TestVenueMatcherResolve:
    @patch('src.models.danslogen.venue_mapper.load_venue_map')
    def test_resolves_from_venue_mapper(self, mock_load_venue_map):
        mock_load_venue_map.return_value = {"Arena": "Q100"}
        matcher = VenueMatcher()
        result = matcher.resolve("Arena")

        assert result == "Q100"

    @patch('src.models.danslogen.venue_mapper.load_venue_map')
    def test_returns_none_when_no_match_and_no_client(self, mock_load_venue_map):
        mock_load_venue_map.return_value = {}
        matcher = VenueMatcher(client=None)
        result = matcher.resolve("Unknown Venue")

        assert result is None

    @patch('src.models.danslogen.venue_mapper.load_venue_map')
    def test_falls_back_to_bygdegardarna(self, mock_load_venue_map):
        mock_load_venue_map.return_value = {}
        byg_venues = {
            "Test Hall": {"qid": "Q200", "title": "Test Hall", "position": {"lat": 59.0, "lng": 18.0}},
        }
        matcher = VenueMatcher(byg_venues=byg_venues)
        result = matcher.resolve("Test Hall")

        assert result == "Q200"

    @patch('src.models.danslogen.venue_mapper.load_venue_map')
    def test_resolves_partial_match_from_venue_mapper(self, mock_load_venue_map):
        mock_load_venue_map.return_value = {"Allhem": "Q123"}
        matcher = VenueMatcher()
        result = matcher.resolve("Allhem i Färgelanda")

        assert result == "Q123"
