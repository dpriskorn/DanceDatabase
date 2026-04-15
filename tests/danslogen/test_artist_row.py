import pytest
from unittest.mock import MagicMock

from src.models.danslogen.artist_row import DanslogenArtistRow


class TestDanslogenArtistRow:
    def test_parses_all_fields(self):
        row = MagicMock()
        cells = [
            MagicMock(
                get_text=MagicMock(return_value="Tommys"),
                find=MagicMock(return_value=None)
            ),
            MagicMock(
                get_text=MagicMock(return_value=""),
                find=MagicMock(return_value=MagicMock(get=MagicMock(return_value="http://www.tommys-musik.fi")))
            ),
            MagicMock(
                get_text=MagicMock(return_value=""),
                find=MagicMock(return_value=MagicMock(get=MagicMock(return_value="https://www.facebook.com/test")))
            ),
            MagicMock(
                get_text=MagicMock(return_value=""),
                find=MagicMock(return_value=MagicMock(get=MagicMock(return_value="/dansband/spelplan/tommys_finland")))
            ),
        ]
        row.find_all = MagicMock(return_value=cells)

        result = DanslogenArtistRow.from_row(row)

        assert result is not None
        assert result.name == "Tommys"
        assert result.website == "http://www.tommys-musik.fi"
        assert result.facebook == "https://www.facebook.com/test"
        assert result.spelplan_id == "tommys_finland"

    def test_parses_minimal_row(self):
        row = MagicMock()
        cells = [
            MagicMock(
                get_text=MagicMock(return_value="TestBand"),
                find=MagicMock(return_value=None)
            ),
            MagicMock(get_text=MagicMock(return_value=""), find=MagicMock(return_value=None)),
            MagicMock(get_text=MagicMock(return_value=""), find=MagicMock(return_value=None)),
            MagicMock(get_text=MagicMock(return_value=""), find=MagicMock(return_value=None)),
        ]
        row.find_all = MagicMock(return_value=cells)

        result = DanslogenArtistRow.from_row(row)

        assert result is not None
        assert result.name == "TestBand"
        assert result.website == ""
        assert result.facebook == ""
        assert result.spelplan_id == ""

    def test_returns_none_for_too_few_cells(self):
        row = MagicMock()
        cells = [
            MagicMock(get_text=MagicMock(return_value="Test")),
        ]
        row.find_all = MagicMock(return_value=cells)

        result = DanslogenArtistRow.from_row(row)

        assert result is None

    def test_returns_none_for_empty_name(self):
        row = MagicMock()
        cells = [
            MagicMock(get_text=MagicMock(return_value="")),
            MagicMock(get_text=MagicMock(return_value="")),
            MagicMock(get_text=MagicMock(return_value="")),
            MagicMock(get_text=MagicMock(return_value="")),
        ]
        row.find_all = MagicMock(return_value=cells)

        result = DanslogenArtistRow.from_row(row)

        assert result is None

    def test_extracts_spelplan_id_correctly(self):
        row = MagicMock()
        cells = [
            MagicMock(get_text=MagicMock(return_value="Allstars")),
            MagicMock(get_text=MagicMock(return_value=""), find=MagicMock(return_value=None)),
            MagicMock(get_text=MagicMock(return_value=""), find=MagicMock(return_value=None)),
            MagicMock(
                get_text=MagicMock(return_value=""),
                find=MagicMock(return_value=MagicMock(get=MagicMock(return_value="/dansband/spelplan/allstars")))
            ),
        ]
        row.find_all = MagicMock(return_value=cells)

        result = DanslogenArtistRow.from_row(row)

        assert result is not None
        assert result.spelplan_id == "allstars"

    def test_strips_whitespace_from_name(self):
        row = MagicMock()
        cells = [
            MagicMock(get_text=MagicMock(return_value="  TestBand  ")),
            MagicMock(get_text=MagicMock(return_value=""), find=MagicMock(return_value=None)),
            MagicMock(get_text=MagicMock(return_value=""), find=MagicMock(return_value=None)),
            MagicMock(get_text=MagicMock(return_value=""), find=MagicMock(return_value=None)),
        ]
        row.find_all = MagicMock(return_value=cells)

        result = DanslogenArtistRow.from_row(row)

        assert result is not None
        assert result.name == "TestBand"