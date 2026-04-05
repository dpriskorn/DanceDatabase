import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.models.danslogen.model import Danslogen, scrape_month


class TestDanslogenFetchMonth:
    @patch('src.models.danslogen.model.requests.get')
    def test_fetch_month_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = '<html><table class="danceprogram"></table></html>'
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        scraper = Danslogen()
        scraper.fetch_month('april')

        assert scraper.soup is not None
        mock_get.assert_called_once_with('https://www.danslogen.se/dansprogram/april')
        mock_response.raise_for_status.assert_called_once()


class TestDanslogenMapBandQid:
    def test_map_band_qid_exact_match(self):
        scraper = Danslogen()
        with patch('src.models.danslogen.model.BAND_QID_MAP', {'TestBand': 'Q123'}):
            result = scraper.map_band_qid('TestBand')
            assert result == 'Q123'

    def test_map_band_qid_case_insensitive(self):
        scraper = Danslogen()
        with patch('src.models.danslogen.model.BAND_QID_MAP', {'TestBand': 'Q123'}):
            result = scraper.map_band_qid('testband')
            assert result == 'Q123'

    def test_map_band_qid_no_match(self):
        scraper = Danslogen()
        with patch('src.models.danslogen.model.BAND_QID_MAP', {}):
            result = scraper.map_band_qid('UnknownBand')
            assert result is None

    def test_map_band_qid_fuzzy_match(self):
        scraper = Danslogen()
        with patch('src.models.danslogen.model.BAND_QID_MAP', {'Lasse Stefanz': 'Q270'}):
            result = scraper.map_band_qid('Lasse Stefanz orkester')
            assert result == 'Q270'


class TestDanslogenMapVenueQid:
    def test_map_venue_qid_partial_match(self):
        scraper = Danslogen()
        with patch('src.models.danslogen.model.VENUE_QID_MAP', {'Allhem': 'Q123'}):
            result = scraper.map_venue_qid('Allhem i Färgelanda')
            assert result == 'Q123'

    def test_map_venue_qid_no_match(self):
        scraper = Danslogen()
        with patch('src.models.danslogen.model.VENUE_QID_MAP', {}):
            result = scraper.map_venue_qid('UnknownVenue')
            assert result is None


class TestDanslogenAddVenueQid:
    def test_add_venue_qid(self):
        scraper = Danslogen()
        with patch('src.models.danslogen.model.VENUE_QID_MAP', {}):
            scraper.add_venue_qid('TestVenue', 'Q999')
            assert scraper.map_venue_qid('TestVenue') == 'Q999'


class TestDanslogenParseWeekdayDay:
    def test_parse_weekday_day_two_parts(self):
        scraper = Danslogen()
        weekday, day = scraper.parse_weekday_day('Sön 5')
        assert weekday == 'Sön'
        assert day == '5'

    def test_parse_weekday_day_single_part(self):
        scraper = Danslogen()
        weekday, day = scraper.parse_weekday_day('Sön')
        assert weekday == 'Sön'
        assert day == ''


class TestDanslogenParseTimeRange:
    def test_parse_time_range_with_dash(self):
        scraper = Danslogen()
        start, end = scraper.parse_time_range('18.00-22.00')
        assert start == '18.00'
        assert end == '22.00'

    def test_parse_time_range_empty(self):
        scraper = Danslogen()
        start, end = scraper.parse_time_range('')
        assert start == ''
        assert end == ''

    def test_parse_time_range_whitespace_only(self):
        scraper = Danslogen()
        start, end = scraper.parse_time_range('   ')
        assert start == ''
        assert end == ''

    def test_parse_time_range_no_dash(self):
        scraper = Danslogen()
        start, end = scraper.parse_time_range('18.00')
        assert start == '18.00'
        assert end == ''


class TestDanslogenParseDate:
    def test_parse_date_valid(self):
        scraper = Danslogen()
        result = scraper.parse_date('5', 'april', 2026)
        assert result is not None
        assert result.day == 5
        assert result.month == 4
        assert result.year == 2026

    def test_parse_date_invalid_day(self):
        scraper = Danslogen()
        result = scraper.parse_date('invalid', 'april', 2026)
        assert result is None

    def test_parse_date_case_insensitive_month(self):
        scraper = Danslogen()
        result = scraper.parse_date('5', 'APRIL', 2026)
        assert result is not None
        assert result.month == 4


class TestDanslogenScrapeMonth:
    @patch('src.models.danslogen.model.requests.get')
    def test_scrape_month_fetches_page(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = '<html><table class="danceprogram"><tr class="r1"></tr></table></html>'
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with patch.object(DancedbClient, 'get_or_create_band', return_value=None):
            with patch.object(Danslogen, 'parse_row', return_value=None):
                scraper = Danslogen()
                scraper.scrape_month('april')

        mock_get.assert_called()


class TestScrapeMonthFunction:
    @patch('src.models.danslogen.model.Danslogen.scrape_month')
    def test_scrape_month_function(self, mock_scrape):
        mock_scrape.return_value = []
        result = scrape_month('april')
        mock_scrape.assert_called_once_with('april')
        assert result == []


class TestDanslogenParseRow:
    @patch('src.models.danslogen.model.DancedbClient')
    @patch('src.models.danslogen.model.click')
    def test_parse_row_with_valid_data(self, mock_click, mock_dancedb_client):
        from src.models.danslogen.table_row import DanslogenTableRow
        from src.models.dance_event import DanceEvent

        mock_dancedb_instance = MagicMock()
        mock_dancedb_instance.get_or_create_band.return_value = None
        mock_dancedb_client.return_value = mock_dancedb_instance

        mock_row = MagicMock()
        mock_cells = [
            MagicMock(get_text=MagicMock(return_value="Sön")),
            MagicMock(get_text=MagicMock(return_value="5")),
            MagicMock(get_text=MagicMock(return_value="18.00-22.00")),
            MagicMock(get_text=MagicMock(return_value="TestBand")),
            MagicMock(get_text=MagicMock(return_value="TestVenue")),
            MagicMock(get_text=MagicMock(return_value="Färgelanda")),
            MagicMock(get_text=MagicMock(return_value="Färgelanda")),
            MagicMock(get_text=MagicMock(return_value="Västra Götaland")),
            MagicMock(get_text=MagicMock(return_value="")),
            MagicMock(get_text=MagicMock(return_value="")),
        ]
        mock_row.find_all = MagicMock(return_value=mock_cells)

        with patch('src.models.danslogen.model.BAND_QID_MAP', {'TestBand': 'Q123'}):
            with patch('src.models.danslogen.model.VENUE_QID_MAP', {'TestVenue': 'Q456'}):
                scraper = Danslogen()
                scraper.dancedb_client = mock_dancedb_instance
                result = scraper.parse_row(mock_row, 'april')

        assert result is not None
        assert isinstance(result, DanceEvent)
        assert result.location == 'TestVenue'


from src.models.dancedb_client import DancedbClient