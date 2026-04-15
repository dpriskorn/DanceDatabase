import pytest
from unittest.mock import MagicMock

from src.models.danslogen.table_row import (
    DanslogenTableRow,
    InvalidRowError,
    TIME_RANGE_PATTERN,
    VALID_WEEKDAYS,
)


class TestTimeRangePattern:
    def test_matches_valid_time_range(self):
        assert TIME_RANGE_PATTERN.match("18.00-22.00")
        assert TIME_RANGE_PATTERN.match("8.00-22.00")
        assert TIME_RANGE_PATTERN.match("18.00-2.00")

    def test_does_not_match_non_time_range(self):
        assert not TIME_RANGE_PATTERN.match("Streaplers")
        assert not TIME_RANGE_PATTERN.match("")
        assert not TIME_RANGE_PATTERN.match("band name")


class TestValidWeekdays:
    def test_valid_weekdays(self):
        assert "Mån" in VALID_WEEKDAYS
        assert "Tis" in VALID_WEEKDAYS
        assert "Ons" in VALID_WEEKDAYS
        assert "Tor" in VALID_WEEKDAYS
        assert "Fre" in VALID_WEEKDAYS
        assert "Lör" in VALID_WEEKDAYS
        assert "Sön" in VALID_WEEKDAYS

    def test_invalid_weekdays(self):
        assert "Monday" not in VALID_WEEKDAYS
        assert "" not in VALID_WEEKDAYS


class TestDanslogenTableRowFromRow:
    def create_mock_row(self, cell_texts: list[str]) -> MagicMock:
        mock_row = MagicMock()
        mock_cells = []
        for text in cell_texts:
            mock_cell = MagicMock()
            mock_cell.get_text.return_value = text
            mock_cells.append(mock_cell)
        mock_row.find_all.return_value = mock_cells
        return mock_row

    def test_raises_when_band_contains_time_range(self):
        row = self.create_mock_row([
            "", "Ons", "3", "", "18.00-22.00", "Streaplers",
            "Brunnen Eringsboda", "Eringsboda", "Ronneby", "Blekinge"
        ])
        with pytest.raises(InvalidRowError) as exc_info:
            DanslogenTableRow.from_row(row)
        assert "18.00-22.00" in str(exc_info.value)
        assert "column mapping error" in str(exc_info.value)

    def test_raises_when_day_not_digit(self):
        row = self.create_mock_row([
            "Ons", "abc", "18.00-22.00", "Streaplers", "Streaplers",
            "Brunnen Eringsboda", "Eringsboda", "Ronneby", "Blekinge"
        ])
        with pytest.raises(InvalidRowError) as exc_info:
            DanslogenTableRow.from_row(row)
        assert "Day field is not a valid number" in str(exc_info.value)

    def test_raises_when_weekday_invalid(self):
        row = self.create_mock_row([
            "Monday", "3", "18.00-22.00", "Streaplers", "Streaplers",
            "Brunnen Eringsboda", "Eringsboda", "Ronneby", "Blekinge"
        ])
        with pytest.raises(InvalidRowError) as exc_info:
            DanslogenTableRow.from_row(row)
        assert "Weekday" in str(exc_info.value)
        assert "not in valid weekdays" in str(exc_info.value)

    def test_parses_valid_row(self):
        row = self.create_mock_row([
            "Ons", "3", "18.00-22.00", "Streaplers", "Streaplers",
            "Brunnen Eringsboda", "Eringsboda", "Ronneby", "Blekinge"
        ])
        result = DanslogenTableRow.from_row(row)
        assert result is not None
        assert result.weekday == "Ons"
        assert result.day == "3"
        assert result.time == "18.00-22.00"
        assert result.band == "Streaplers"
        assert result.venue == "Streaplers"
        assert result.ort == "Brunnen Eringsboda"

    def test_parses_row_with_empty_first_cell(self):
        row = self.create_mock_row([
            "", "Ons", "3", "18.00-22.00", "Streaplers", "Streaplers",
            "Brunnen Eringsboda", "Eringsboda", "Ronneby", "Blekinge"
        ])
        result = DanslogenTableRow.from_row(row)
        assert result is not None
        assert result.weekday == "Ons"
        assert result.day == "3"

    def test_returns_none_when_too_few_cells(self):
        row = self.create_mock_row(["Ons", "3"])
        result = DanslogenTableRow.from_row(row)
        assert result is None

    def test_returns_none_when_band_empty(self):
        row = self.create_mock_row([
            "Ons", "3", "18.00-22.00", "", "Streaplers",
            "Brunnen Eringsboda", "Eringsboda", "Ronneby", "Blekinge"
        ])
        result = DanslogenTableRow.from_row(row)
        assert result is None