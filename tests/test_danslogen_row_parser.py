import pytest
from unittest.mock import MagicMock, patch

from src.models.danslogen.row_parser import RowParser
from src.models.danslogen.venue_matcher import VenueMatcher
from src.models.danslogen.band_mapper import BandMapper


class TestRowParserParse:
    def test_parses_valid_row(self):
        mock_venue_matcher = MagicMock(spec=VenueMatcher)
        mock_venue_matcher.resolve.return_value = "Q100"
        mock_band_mapper = MagicMock(spec=BandMapper)
        mock_band_mapper.resolve.return_value = "Q200"

        parser = RowParser(venue_matcher=mock_venue_matcher, band_mapper=mock_band_mapper)

        row = {
            "band": "TestBand",
            "venue": "TestHall",
            "ort": "TestCity",
            "day": "5",
            "time": "18.00-22.00",
            "ovrigt": "Test info",
        }

        event = parser.parse(row, "april")

        assert event is not None
        assert event.label["sv"] == "TestBand på TestHall"
        assert event.identifiers.dancedatabase.venue == "Q100"

    def test_skips_when_band_not_found(self):
        mock_venue_matcher = MagicMock(spec=VenueMatcher)
        mock_venue_matcher.resolve.return_value = "Q100"
        mock_band_mapper = MagicMock(spec=BandMapper)
        mock_band_mapper.resolve.return_value = None

        parser = RowParser(venue_matcher=mock_venue_matcher, band_mapper=mock_band_mapper)

        row = {
            "band": "UnknownBand",
            "venue": "TestHall",
            "ort": "TestCity",
            "day": "5",
        }

        event = parser.parse(row, "april")

        assert event is None

    def test_skips_when_venue_not_found(self):
        mock_venue_matcher = MagicMock(spec=VenueMatcher)
        mock_venue_matcher.resolve.return_value = None
        mock_band_mapper = MagicMock(spec=BandMapper)
        mock_band_mapper.resolve.return_value = "Q200"

        parser = RowParser(venue_matcher=mock_venue_matcher, band_mapper=mock_band_mapper)

        row = {
            "band": "TestBand",
            "venue": "UnknownHall",
            "ort": "TestCity",
            "day": "5",
        }

        event = parser.parse(row, "april")

        assert event is None


class TestRowParserParseDate:
    def test_parses_valid_date(self):
        mock_venue_matcher = MagicMock(spec=VenueMatcher)
        mock_venue_matcher.resolve.return_value = "Q100"
        mock_band_mapper = MagicMock(spec=BandMapper)
        mock_band_mapper.resolve.return_value = "Q200"

        parser = RowParser(venue_matcher=mock_venue_matcher, band_mapper=mock_band_mapper)

        result = parser._parse_date("5", "april", 2026)

        assert result is not None

    def test_handles_invalid_day(self):
        mock_venue_matcher = MagicMock(spec=VenueMatcher)
        mock_venue_matcher.resolve.return_value = "Q100"
        mock_band_mapper = MagicMock(spec=BandMapper)
        mock_band_mapper.resolve.return_value = "Q200"

        parser = RowParser(venue_matcher=mock_venue_matcher, band_mapper=mock_band_mapper)

        result = parser._parse_date("invalid", "april")

        assert result is None


class TestRowParserParseDatetime:
    def test_parses_time_range(self):
        from datetime import datetime
        from config import CET

        mock_venue_matcher = MagicMock(spec=VenueMatcher)
        mock_venue_matcher.resolve.return_value = "Q100"
        mock_band_mapper = MagicMock(spec=BandMapper)
        mock_band_mapper.resolve.return_value = "Q200"

        parser = RowParser(venue_matcher=mock_venue_matcher, band_mapper=mock_band_mapper)

        date = datetime(2026, 4, 5, tzinfo=CET)
        start, end = parser._parse_datetime(date, "18.00-22.00")

        assert start is not None
        assert end is not None

    def test_handles_empty_time(self):
        from datetime import datetime
        from config import CET

        mock_venue_matcher = MagicMock(spec=VenueMatcher)
        mock_venue_matcher.resolve.return_value = "Q100"
        mock_band_mapper = MagicMock(spec=BandMapper)
        mock_band_mapper.resolve.return_value = "Q200"

        parser = RowParser(venue_matcher=mock_venue_matcher, band_mapper=mock_band_mapper)

        date = datetime(2026, 4, 5, tzinfo=CET)
        start, end = parser._parse_datetime(date, "")

        assert start is None
        assert end is None