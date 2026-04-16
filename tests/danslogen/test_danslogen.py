from unittest.mock import MagicMock, patch

from src.models.danslogen.main import Danslogen, scrape_month
from src.utils.fuzzy_models import FuzzyMatchResultQid


class TestDanslogenFetchMonth:
    @patch("src.models.danslogen.main.requests.get")
    def test_fetch_month_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = '<html><table class="danceprogram"></table></html>'
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        scraper = Danslogen(interactive=False)
        scraper.fetch_month("april")

        assert scraper.soup is not None
        mock_get.assert_called_once_with("https://www.danslogen.se/dansprogram/april")
        mock_response.raise_for_status.assert_called_once()


class TestDanslogenMapBandQid:
    @patch("src.models.danslogen.band_mapper.load_band_map")
    def test_map_band_qid_exact_match(self, mock_load_band_map):
        mock_load_band_map.return_value = {"testband": "Q123"}
        scraper = Danslogen(interactive=False)
        result = scraper.map_band_qid("TestBand")
        assert result == "Q123"

    @patch("src.models.danslogen.band_mapper.load_band_map")
    def test_map_band_qid_case_insensitive(self, mock_load_band_map):
        mock_load_band_map.return_value = {"testband": "Q123"}
        scraper = Danslogen(interactive=False)
        result = scraper.map_band_qid("testband")
        assert result == "Q123"

    @patch("src.models.danslogen.band_mapper.load_band_map")
    def test_map_band_qid_no_match(self, mock_load_band_map):
        mock_load_band_map.return_value = {}
        scraper = Danslogen(interactive=False)
        result = scraper.map_band_qid("UnknownBand")
        assert result is None

    @patch("src.models.danslogen.band_mapper.load_band_map")
    @patch("src.models.danslogen.band_mapper.fuzzy_match_qid")
    def test_map_band_qid_fuzzy_match(self, mock_fuzzy, mock_load_band_map):
        mock_load_band_map.return_value = {"lasse stefanz": "Q270"}
        mock_fuzzy.return_value = FuzzyMatchResultQid(matched_label="Lasse Stefanz", qid="Q270", score=90, cleaned_input="lasse stefanz orkester", false_friend=False)
        scraper = Danslogen(interactive=False)
        result = scraper.map_band_qid("Lasse Stefanz orkester")
        assert result == "Q270"


class TestDanslogenMapVenueQid:
    @patch("src.models.danslogen.venue_mapper.load_venue_map")
    def test_map_venue_qid_partial_match(self, mock_load_venue_map):
        mock_load_venue_map.return_value = {"Allhem": "Q123"}
        scraper = Danslogen(interactive=False)
        result = scraper.map_venue_qid("Allhem i Färgelanda")
        assert result == "Q123"

    @patch("src.models.danslogen.venue_mapper.load_venue_map")
    def test_map_venue_qid_no_match(self, mock_load_venue_map):
        mock_load_venue_map.return_value = {}
        scraper = Danslogen(interactive=False)
        result = scraper.map_venue_qid("UnknownVenue")
        assert result is None

    @patch("src.models.danslogen.venue_mapper.load_venue_map")
    def test_add_venue_qid(self, mock_load_venue_map):
        mock_load_venue_map.return_value = {}
        scraper = Danslogen(interactive=False)
        # Initialize _venue_map by calling resolve (which calls _get_venue_map)
        scraper.venue_mapper.resolve("AnyVenue")
        scraper.add_venue_qid("TestVenue", "Q456")
        assert scraper.venue_mapper._venue_map.get("testvenue") == "Q456"


class TestDanslogenScrapeMonth:
    @patch("src.models.danslogen.main.requests.get")
    def test_scrape_month_fetches_page(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = '<html><table class="danceprogram"><tr class="r1"></tr></table></html>'
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        scraper = Danslogen(interactive=False)
        events = scraper.scrape_month("april")

        assert len(events) == 0
        mock_get.assert_called()


class TestScrapeMonthFunction:
    @patch("src.models.danslogen.main.Danslogen.scrape_month")
    def test_scrape_month_function(self, mock_scrape):
        mock_scrape.return_value = []
        scrape_month("april")
        mock_scrape.assert_called_once_with("april")


class TestDanslogenParseRow:
    @patch("src.models.danslogen.band_mapper.load_band_map")
    @patch("src.models.danslogen.venue_mapper.load_venue_map")
    @patch("src.models.danslogen.main.DancedbClient")
    def test_parse_row_with_valid_data(self, mock_client, mock_venue_map, mock_band_map):
        mock_band_map.return_value = {"testband": "Q123"}
        mock_venue_map.return_value = {"TestVenue": "Q456"}
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance

        from bs4 import BeautifulSoup

        html = "<table><tr><td>Sön</td><td>5</td><td>18.00-22.00</td><td>TestBand</td><td>TestVenue</td><td>Färgelanda</td><td>Färgelanda</td><td>Västra Götaland</td><td></td><td></td></tr></table>"
        soup = BeautifulSoup(html, "lxml")
        row = soup.find("tr")

        scraper = Danslogen(interactive=False)
        scraper.dancedb_client = mock_client_instance
        result = scraper.parse_row(row, "april")

        assert result is not None
        assert result.location == "TestVenue"
