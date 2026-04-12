import pytest
from unittest.mock import MagicMock, patch

from src.models.danslogen.venue_matcher import VenueMatcher


class TestVenueMatcherFindInStaticMap:
    @patch('src.models.danslogen.venue_matcher.VENUE_QID_MAP', {"TestHall": "Q123"})
    def test_finds_exact_match(self):
        matcher = VenueMatcher()
        result = matcher._find_in_static_map("TestHall")

        assert result == "Q123"

    @patch('src.models.danslogen.venue_matcher.VENUE_QID_MAP', {"Test Hall": "Q123"})
    def test_returns_none_for_case_mismatch(self):
        matcher = VenueMatcher()
        result = matcher._find_in_static_map("testhall")

        assert result is None

    def test_falls_back_to_fuzzy(self):
        with patch('src.models.danslogen.venue_matcher.VENUE_QID_MAP', {}):
            with patch('src.models.danslogen.venue_matcher.fuzzy_match_qid') as mock_fuzzy:
                mock_fuzzy.return_value = ("Test Hall", "Q123", 95)
                matcher = VenueMatcher()
                result = matcher._find_in_static_map("Testhal")

                assert result == "Q123"
                mock_fuzzy.assert_called_once()


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


class TestVenueMatcherFindInDancedb:
    def test_finds_exact_match(self):
        db_venues = {
            "Q789": {"label": "Dance Hall"},
        }
        matcher = VenueMatcher(db_venues=db_venues)
        result = matcher._find_in_dancedb("Dance Hall")

        assert result == "Q789"

    def test_returns_none_for_empty_db(self):
        matcher = VenueMatcher(db_venues=None)
        result = matcher._find_in_dancedb("Dance Hall")

        assert result is None


class TestVenueMatcherResolve:
    @patch('src.models.danslogen.venue_matcher.VENUE_QID_MAP', {"Arena": "Q100"})
    def test_resolves_from_static_map_first(self):
        matcher = VenueMatcher()
        result = matcher.resolve("Arena")

        assert result == "Q100"

    @patch('src.models.danslogen.venue_matcher.VENUE_QID_MAP', {})
    def test_returns_none_when_no_match_and_no_client(self):
        matcher = VenueMatcher(client=None)
        result = matcher.resolve("Unknown Venue")

        assert result is None