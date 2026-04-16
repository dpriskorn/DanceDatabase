from unittest.mock import MagicMock, patch

from src.models.danslogen.band_mapper import BandMapper


class TestBandMapperResolve:
    @patch("src.models.danslogen.band_mapper.load_band_map")
    def test_finds_exact_match(self, mock_load):
        mock_load.return_value = {"testband": "Q200"}
        mapper = BandMapper()
        result = mapper.resolve("TestBand")

        assert result == "Q200"

    @patch("src.models.danslogen.band_mapper.load_band_map")
    def test_finds_case_insensitive(self, mock_load):
        mock_load.return_value = {"testband": "Q200"}
        mapper = BandMapper()
        result = mapper.resolve("testband")

        assert result == "Q200"

    @patch("src.models.danslogen.band_mapper.load_band_map")
    @patch("src.models.danslogen.band_mapper.fuzzy_match_qid")
    def test_falls_back_to_fuzzy(self, mock_fuzzy, mock_load):
        mock_load.return_value = {"test band": "Q200"}
        mock_fuzzy.return_value = ("Test Band", "Q200", 90, "testbnad")
        mapper = BandMapper()
        result = mapper.resolve("Testbnad")

        assert result == "Q200"
        mock_fuzzy.assert_called_once()

    @patch("src.models.danslogen.band_mapper.load_band_map")
    def test_returns_none_when_not_found_and_no_client(self, mock_load):
        mock_load.return_value = {}
        mapper = BandMapper(client=None)
        result = mapper.resolve("Unknown Band")

        assert result is None

    @patch("src.models.danslogen.band_mapper.load_band_map")
    def test_returns_none_for_empty_band_name(self, mock_load):
        mock_load.return_value = {}
        mapper = BandMapper()
        result = mapper.resolve("")

        assert result is None


class TestBandMapperWithClient:
    @patch("src.models.danslogen.band_mapper.load_danslogen_artists")
    @patch("src.models.danslogen.band_mapper.load_band_map")
    @patch("src.models.danslogen.band_mapper.fuzzy_match_qid", return_value=None)
    def test_uses_client_when_no_static_match(self, mock_fuzzy, mock_load, mock_danslogen):
        mock_load.return_value = {}
        mock_danslogen.return_value = {}
        mock_client = MagicMock()
        mock_client.get_or_create_band.return_value = "Q300"
        mapper = BandMapper(client=mock_client)
        result = mapper.resolve("NewBand")

        assert result == "Q300"
        mock_client.get_or_create_band.assert_called_once_with("NewBand", spelplan_id="")

    @patch("src.models.danslogen.band_mapper.load_danslogen_artists")
    @patch("src.models.danslogen.band_mapper.load_band_map")
    @patch("src.models.danslogen.band_mapper.fuzzy_match_qid", return_value=None)
    def test_passes_spelplan_id_to_client(self, mock_fuzzy, mock_load, mock_danslogen):
        mock_load.return_value = {}
        mock_danslogen.return_value = {"newband": {"name": "NewBand", "spelplan_id": "kent_henke"}}
        mock_client = MagicMock()
        mock_client.get_or_create_band.return_value = "Q300"
        mapper = BandMapper(client=mock_client)
        result = mapper.resolve("NewBand")

        assert result == "Q300"
        mock_client.get_or_create_band.assert_called_once_with("NewBand", spelplan_id="kent_henke")
