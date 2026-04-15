from bs4 import BeautifulSoup
from unittest.mock import MagicMock, patch

from src.models.danslogen.events.table_row import DanslogenTableRow


class TestDanslogenParseDatetime:
    """Test full datetime parsing in Danslogen.parse_row."""

    @patch('src.models.danslogen.band_mapper.load_band_map')
    @patch('src.models.danslogen.venue_mapper.load_venue_map')
    def test_parses_row_like_html_example(self, mock_load_venue, mock_load_band):
        """Test row with exact HTML structure user provided.
        
        HTML:
        <tr class="r9351">
            <td></td><td>Mån</td><td>13</td>
            <td>19.30-23.00</td>
            <td>Streaplers</td>
            <td>Ätrasalen</td>
            <td>Vessigebro</td>
            <td>Falkenberg</td>
            <td>Halland</td>
            <td></td>
        </tr>
        """
        from src.models.danslogen.main import Danslogen

        mock_load_band.return_value = {'streaplers': 'Q123'}
        mock_load_venue.return_value = {'ätrasalen': 'Q456'}

        html = '''<tr class="r9351">
            <td></td>
            <td>Mån</td>
            <td>13</td>
            <td>19.30-23.00</td>
            <td>Streaplers</td>
            <td>Ätrasalen</td>
            <td>Vessigebro</td>
            <td>Falkenberg</td>
            <td>Halland</td>
            <td></td>
        </tr>'''
        
        scraper = Danslogen(month="april", interactive=False)
        soup = BeautifulSoup(html, "lxml")
        row = soup.find("tr")
        
        result = scraper.parse_row(row, "april")
        
        assert result is not None
        assert result.start_timestamp.day == 13
        assert result.start_timestamp.hour == 19
        assert result.start_timestamp.minute == 30
        assert result.end_timestamp.day == 13
        assert result.end_timestamp.hour == 23
        assert result.end_timestamp.minute == 0


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
