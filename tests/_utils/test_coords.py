import pytest

from src.utils.coords import parse_coords


class TestParseCoords:
    def test_simple_comma_format(self):
        result = parse_coords("59.355601,18.0993459")
        assert result == {"lat": 59.355601, "lng": 18.0993459}

    def test_dict_format(self):
        result = parse_coords('{"lat": 59.355601, "lng": 18.0993459}')
        assert result == {"lat": 59.355601, "lng": 18.0993459}

    def test_dict_format_with_newlines_and_spaces(self):
        result = parse_coords('{"lat": 59.355601,\n    "lng": 18.0993459}')
        assert result == {"lat": 59.355601, "lng": 18.0993459}

    def test_dict_format_with_spaces_in_values(self):
        result = parse_coords('{ "lat": 59.355601, "lng": 18.0993459 }')
        assert result == {"lat": 59.355601, "lng": 18.0993459}

    def test_empty_string(self):
        assert parse_coords("") is None

    def test_whitespace_only(self):
        assert parse_coords("   ") is None

    def test_invalid_format(self):
        assert parse_coords("not valid") is None

    def test_missing_lng_key(self):
        assert parse_coords('{"lat": 59.355601}') is None

    def test_missing_lat_key(self):
        assert parse_coords('{"lng": 18.0993459}') is None

    def test_only_one_value(self):
        assert parse_coords("59.355601") is None

    def test_extra_commas(self):
        assert parse_coords("59.355601,18.0993459,extra") is None