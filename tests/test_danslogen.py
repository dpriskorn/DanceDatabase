import pytest
from unittest.mock import MagicMock

from src.models.danslogen.table_row import DanslogenTableRow


class TestDanslogenTableRow:
    def test_parses_normal_row(self):
        row = MagicMock()
        cells = [
            MagicMock(get_text=MagicMock(return_value="Sön")),
            MagicMock(get_text=MagicMock(return_value="5")),
            MagicMock(get_text=MagicMock(return_value="18.00-22.00")),
            MagicMock(get_text=MagicMock(return_value="Frippez")),
            MagicMock(get_text=MagicMock(return_value="Allhem")),
            MagicMock(get_text=MagicMock(return_value="Färgelanda")),
            MagicMock(get_text=MagicMock(return_value="Färgelanda")),
            MagicMock(get_text=MagicMock(return_value="Västra Götaland")),
            MagicMock(get_text=MagicMock(return_value="Föranmälan 073805566")),
        ]
        row.find_all = MagicMock(return_value=cells)

        result = DanslogenTableRow.from_row(row)

        assert result is not None
        assert result.weekday == "Sön"
        assert result.day == "5"
        assert result.time == "18.00-22.00"
        assert result.band == "Frippez"
        assert result.venue == "Allhem"
        assert result.ort == "Färgelanda"
        assert result.kommun == "Färgelanda"
        assert result.lan == "Västra Götaland"
        assert result.ovrigt == "Föranmälan 073805566"

    def test_parses_row_with_empty_first_cell(self):
        row = MagicMock()
        cells = [
            MagicMock(get_text=MagicMock(return_value="")),
            MagicMock(get_text=MagicMock(return_value="Sön")),
            MagicMock(get_text=MagicMock(return_value="28")),
            MagicMock(get_text=MagicMock(return_value="18.00-22.00")),
            MagicMock(get_text=MagicMock(return_value="Frippez")),
            MagicMock(get_text=MagicMock(return_value="Allhem")),
            MagicMock(get_text=MagicMock(return_value="Färgelanda")),
            MagicMock(get_text=MagicMock(return_value="Färgelanda")),
            MagicMock(get_text=MagicMock(return_value="Västra Götaland")),
            MagicMock(get_text=MagicMock(return_value="")),
        ]
        row.find_all = MagicMock(return_value=cells)

        result = DanslogenTableRow.from_row(row)

        assert result is not None
        assert result.weekday == "Sön"
        assert result.day == "28"
        assert result.time == "18.00-22.00"
        assert result.band == "Frippez"

    def test_returns_none_for_too_few_cells(self):
        row = MagicMock()
        cells = [
            MagicMock(get_text=MagicMock(return_value="Sön")),
            MagicMock(get_text=MagicMock(return_value="5")),
        ]
        row.find_all = MagicMock(return_value=cells)

        result = DanslogenTableRow.from_row(row)

        assert result is None

    def test_returns_none_for_empty_band(self):
        row = MagicMock()
        cells = [
            MagicMock(get_text=MagicMock(return_value="Sön")),
            MagicMock(get_text=MagicMock(return_value="5")),
            MagicMock(get_text=MagicMock(return_value="18.00-22.00")),
            MagicMock(get_text=MagicMock(return_value="")),
            MagicMock(get_text=MagicMock(return_value="Allhem")),
            MagicMock(get_text=MagicMock(return_value="Färgelanda")),
            MagicMock(get_text=MagicMock(return_value="Färgelanda")),
            MagicMock(get_text=MagicMock(return_value="Västra Götaland")),
            MagicMock(get_text=MagicMock(return_value="")),
            MagicMock(get_text=MagicMock(return_value="")),
        ]
        row.find_all = MagicMock(return_value=cells)

        result = DanslogenTableRow.from_row(row)

        assert result is None

    def test_handles_empty_time(self):
        row = MagicMock()
        cells = [
            MagicMock(get_text=MagicMock(return_value="Sön")),
            MagicMock(get_text=MagicMock(return_value="5")),
            MagicMock(get_text=MagicMock(return_value="")),
            MagicMock(get_text=MagicMock(return_value="Jive")),
            MagicMock(get_text=MagicMock(return_value="Birka Gotland")),
            MagicMock(get_text=MagicMock(return_value="Stockholm")),
            MagicMock(get_text=MagicMock(return_value="Stockholm")),
            MagicMock(get_text=MagicMock(return_value="Stockholm")),
            MagicMock(get_text=MagicMock(return_value="")),
            MagicMock(get_text=MagicMock(return_value="")),
        ]
        row.find_all = MagicMock(return_value=cells)

        result = DanslogenTableRow.from_row(row)

        assert result is not None
        assert result.time == ""
        assert result.band == "Jive"
        assert result.venue == "Birka Gotland"

    def test_handles_empty_venue(self):
        row = MagicMock()
        cells = [
            MagicMock(get_text=MagicMock(return_value="Sön")),
            MagicMock(get_text=MagicMock(return_value="5")),
            MagicMock(get_text=MagicMock(return_value="18.00-22.00")),
            MagicMock(get_text=MagicMock(return_value="Frippez")),
            MagicMock(get_text=MagicMock(return_value="")),
            MagicMock(get_text=MagicMock(return_value="Färgelanda")),
            MagicMock(get_text=MagicMock(return_value="Färgelanda")),
            MagicMock(get_text=MagicMock(return_value="Västra Götaland")),
            MagicMock(get_text=MagicMock(return_value="")),
            MagicMock(get_text=MagicMock(return_value="")),
        ]
        row.find_all = MagicMock(return_value=cells)

        result = DanslogenTableRow.from_row(row)

        assert result is not None
        assert result.venue == ""
        assert result.ort == "Färgelanda"


class TestDanslogenTableRowValidation:
    def test_time_validator_strips_whitespace(self):
        row = MagicMock()
        cells = [
            MagicMock(get_text=MagicMock(return_value="Sön")),
            MagicMock(get_text=MagicMock(return_value="5")),
            MagicMock(get_text=MagicMock(return_value="  18.00-22.00  ")),
            MagicMock(get_text=MagicMock(return_value="Frippez")),
            MagicMock(get_text=MagicMock(return_value="Allhem")),
            MagicMock(get_text=MagicMock(return_value="Färgelanda")),
            MagicMock(get_text=MagicMock(return_value="Färgelanda")),
            MagicMock(get_text=MagicMock(return_value="Västra Götaland")),
            MagicMock(get_text=MagicMock(return_value="")),
            MagicMock(get_text=MagicMock(return_value="")),
        ]
        row.find_all = MagicMock(return_value=cells)

        result = DanslogenTableRow.from_row(row)

        assert result is not None
        assert result.time == "18.00-22.00"

    def test_band_validator_strips_whitespace(self):
        row = MagicMock()
        cells = [
            MagicMock(get_text=MagicMock(return_value="Sön")),
            MagicMock(get_text=MagicMock(return_value="5")),
            MagicMock(get_text=MagicMock(return_value="18.00-22.00")),
            MagicMock(get_text=MagicMock(return_value="  Frippez  ")),
            MagicMock(get_text=MagicMock(return_value="Allhem")),
            MagicMock(get_text=MagicMock(return_value="Färgelanda")),
            MagicMock(get_text=MagicMock(return_value="Färgelanda")),
            MagicMock(get_text=MagicMock(return_value="Västra Götaland")),
            MagicMock(get_text=MagicMock(return_value="")),
            MagicMock(get_text=MagicMock(return_value="")),
        ]
        row.find_all = MagicMock(return_value=cells)

        result = DanslogenTableRow.from_row(row)

        assert result is not None
        assert result.band == "Frippez"

    def test_venue_validator_allows_empty(self):
        row = MagicMock()
        cells = [
            MagicMock(get_text=MagicMock(return_value="Sön")),
            MagicMock(get_text=MagicMock(return_value="5")),
            MagicMock(get_text=MagicMock(return_value="18.00-22.00")),
            MagicMock(get_text=MagicMock(return_value="Frippez")),
            MagicMock(get_text=MagicMock(return_value="")),
            MagicMock(get_text=MagicMock(return_value="Färgelanda")),
            MagicMock(get_text=MagicMock(return_value="Färgelanda")),
            MagicMock(get_text=MagicMock(return_value="Västra Götaland")),
            MagicMock(get_text=MagicMock(return_value="")),
            MagicMock(get_text=MagicMock(return_value="")),
        ]
        row.find_all = MagicMock(return_value=cells)

        result = DanslogenTableRow.from_row(row)

        assert result is not None
        assert result.venue == ""
