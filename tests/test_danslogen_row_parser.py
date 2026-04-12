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

    def test_parses_early_morning_end_time(self):
        from datetime import datetime
        from config import CET

        mock_venue_matcher = MagicMock(spec=VenueMatcher)
        mock_venue_matcher.resolve.return_value = "Q100"
        mock_band_mapper = MagicMock(spec=BandMapper)
        mock_band_mapper.resolve.return_value = "Q200"

        parser = RowParser(venue_matcher=mock_venue_matcher, band_mapper=mock_band_mapper)

        date = datetime(2026, 4, 28, tzinfo=CET)
        start, end = parser._parse_datetime(date, "17.00-02.00")

        assert start is not None
        assert end is not None
        assert start.date() == datetime(2026, 4, 28).date()
        assert end.date() == datetime(2026, 4, 29).date()
        assert end.hour == 2

    def test_parses_single_time_no_dash(self):
        from datetime import datetime
        from config import CET

        mock_venue_matcher = MagicMock(spec=VenueMatcher)
        mock_venue_matcher.resolve.return_value = "Q100"
        mock_band_mapper = MagicMock(spec=BandMapper)
        mock_band_mapper.resolve.return_value = "Q200"

        parser = RowParser(venue_matcher=mock_venue_matcher, band_mapper=mock_band_mapper)

        date = datetime(2026, 4, 5, tzinfo=CET)
        start, end = parser._parse_datetime(date, "20.00")

        assert start is not None
        assert end is None
        assert start.hour == 20

    def test_early_morning_hour_boundary_03(self):
        from datetime import datetime
        from config import CET

        mock_venue_matcher = MagicMock(spec=VenueMatcher)
        mock_venue_matcher.resolve.return_value = "Q100"
        mock_band_mapper = MagicMock(spec=BandMapper)
        mock_band_mapper.resolve.return_value = "Q200"

        parser = RowParser(venue_matcher=mock_venue_matcher, band_mapper=mock_band_mapper)

        date = datetime(2026, 4, 28, tzinfo=CET)
        start, end = parser._parse_datetime(date, "17.00-03.00")

        assert end is not None
        assert end.date() == datetime(2026, 4, 29).date()

    def test_late_night_hour_not_shifted(self):
        from datetime import datetime
        from config import CET

        mock_venue_matcher = MagicMock(spec=VenueMatcher)
        mock_venue_matcher.resolve.return_value = "Q100"
        mock_band_mapper = MagicMock(spec=BandMapper)
        mock_band_mapper.resolve.return_value = "Q200"

        parser = RowParser(venue_matcher=mock_venue_matcher, band_mapper=mock_band_mapper)

        date = datetime(2026, 4, 28, tzinfo=CET)
        start, end = parser._parse_datetime(date, "17.00-04.00")

        assert end is not None
        assert end.date() == datetime(2026, 4, 28).date()

    def test_handles_keyboard_interrupt_on_venue_match(self):
        from src.models.danslogen.venue_matcher import VenueMatcher

        mock_venue_matcher = MagicMock(spec=VenueMatcher)
        mock_venue_matcher.resolve.side_effect = KeyboardInterrupt()
        mock_band_mapper = MagicMock(spec=BandMapper)
        mock_band_mapper.resolve.return_value = "Q200"

        parser = RowParser(venue_matcher=mock_venue_matcher, band_mapper=mock_band_mapper)

        row = {"band": "TestBand", "venue": "TestHall", "ort": "TestOrt", "day": "5", "time": "18.00-22.00"}

        with pytest.raises(KeyboardInterrupt):
            parser.parse(row, "april")

    def test_skips_invalid_date(self):
        from datetime import datetime
        from config import CET
        from src.models.danslogen.venue_matcher import VenueMatcher
        from src.models.danslogen.band_mapper import BandMapper

        mock_venue_matcher = MagicMock(spec=VenueMatcher)
        mock_venue_matcher.resolve.return_value = "Q100"
        mock_band_mapper = MagicMock(spec=BandMapper)
        mock_band_mapper.resolve.return_value = "Q200"

        parser = RowParser(venue_matcher=mock_venue_matcher, band_mapper=mock_band_mapper)

        row = {"band": "TestBand", "venue": "TestHall", "ort": "TestOrt", "day": "invalid", "time": "18.00-22.00"}

        result = parser.parse(row, "april")

        assert result is None

    def test_detects_spf_case_sensitive(self):
        mock_venue_matcher = MagicMock(spec=VenueMatcher)
        mock_venue_matcher.resolve.return_value = "Q100"
        mock_band_mapper = MagicMock(spec=BandMapper)
        mock_band_mapper.resolve.return_value = "Q200"

        parser = RowParser(venue_matcher=mock_venue_matcher, band_mapper=mock_band_mapper)

        dance_styles, instance_of = parser._detect_dance_styles_and_instance("SPF")

        assert dance_styles == ["Q675"]
        assert instance_of == "Q678"

    def test_detects_pro_case_sensitive(self):
        mock_venue_matcher = MagicMock(spec=VenueMatcher)
        mock_venue_matcher.resolve.return_value = "Q100"
        mock_band_mapper = MagicMock(spec=BandMapper)
        mock_band_mapper.resolve.return_value = "Q200"

        parser = RowParser(venue_matcher=mock_venue_matcher, band_mapper=mock_band_mapper)

        dance_styles, instance_of = parser._detect_dance_styles_and_instance("PRO")

        assert dance_styles == ["Q676"]
        assert instance_of == "Q678"

    def test_detects_lansdans_case_insensitive(self):
        mock_venue_matcher = MagicMock(spec=VenueMatcher)
        mock_venue_matcher.resolve.return_value = "Q100"
        mock_band_mapper = MagicMock(spec=BandMapper)
        mock_band_mapper.resolve.return_value = "Q200"

        parser = RowParser(venue_matcher=mock_venue_matcher, band_mapper=mock_band_mapper)

        dance_styles, instance_of = parser._detect_dance_styles_and_instance("länsdans")

        assert dance_styles == ["Q677"]
        assert instance_of == "Q677"

    def test_detects_lansdans_mixed_case(self):
        mock_venue_matcher = MagicMock(spec=VenueMatcher)
        mock_venue_matcher.resolve.return_value = "Q100"
        mock_band_mapper = MagicMock(spec=BandMapper)
        mock_band_mapper.resolve.return_value = "Q200"

        parser = RowParser(venue_matcher=mock_venue_matcher, band_mapper=mock_band_mapper)

        dance_styles, instance_of = parser._detect_dance_styles_and_instance("LänsDans")

        assert dance_styles == ["Q677"]
        assert instance_of == "Q677"

    def test_no_match_pro_lowercase(self):
        mock_venue_matcher = MagicMock(spec=VenueMatcher)
        mock_venue_matcher.resolve.return_value = "Q100"
        mock_band_mapper = MagicMock(spec=BandMapper)
        mock_band_mapper.resolve.return_value = "Q200"

        parser = RowParser(venue_matcher=mock_venue_matcher, band_mapper=mock_band_mapper)

        dance_styles, instance_of = parser._detect_dance_styles_and_instance("pro")

        assert dance_styles == []
        assert instance_of == "Q2"

    def test_no_match_spf_mixed_case(self):
        mock_venue_matcher = MagicMock(spec=VenueMatcher)
        mock_venue_matcher.resolve.return_value = "Q100"
        mock_band_mapper = MagicMock(spec=BandMapper)
        mock_band_mapper.resolve.return_value = "Q200"

        parser = RowParser(venue_matcher=mock_venue_matcher, band_mapper=mock_band_mapper)

        dance_styles, instance_of = parser._detect_dance_styles_and_instance("SpF")

        assert dance_styles == []
        assert instance_of == "Q2"

    def test_empty_ovrigt_default(self):
        mock_venue_matcher = MagicMock(spec=VenueMatcher)
        mock_venue_matcher.resolve.return_value = "Q100"
        mock_band_mapper = MagicMock(spec=BandMapper)
        mock_band_mapper.resolve.return_value = "Q200"

        parser = RowParser(venue_matcher=mock_venue_matcher, band_mapper=mock_band_mapper)

        dance_styles, instance_of = parser._detect_dance_styles_and_instance("")

        assert dance_styles == []
        assert instance_of == "Q2"