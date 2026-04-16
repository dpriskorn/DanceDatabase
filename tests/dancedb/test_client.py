from unittest.mock import MagicMock, patch

import pytest

from src.models.dancedb.client import DancedbClient


class TestDancedbClientSearchBand:
    @patch("src.models.dancedb.client.Login")
    def test_search_band_finds_single_match(self, mock_login):
        mock_login.return_value = MagicMock()

        with patch("src.models.dancedb.client.execute_sparql_query") as mock_sparql:
            mock_sparql.return_value = {"results": {"bindings": [{"item": {"value": "https://dance.wikibase.cloud/wiki/Q123"}}]}}

            client = DancedbClient()
            result = client.search_band("TestBand")

            assert result == "Q123"
            mock_sparql.assert_called_once()

    @patch("src.models.dancedb.client.Login")
    def test_search_band_returns_none_when_no_match(self, mock_login):
        mock_login.return_value = MagicMock()

        with patch("src.models.dancedb.client.execute_sparql_query") as mock_sparql:
            mock_sparql.return_value = {"results": {"bindings": []}}

            client = DancedbClient()
            result = client.search_band("UnknownBand")

            assert result is None

    @patch("src.models.dancedb.client.Login")
    def test_search_band_returns_none_when_multiple_matches(self, mock_login):
        mock_login.return_value = MagicMock()

        with patch("src.models.dancedb.client.execute_sparql_query") as mock_sparql:
            mock_sparql.return_value = {
                "results": {
                    "bindings": [
                        {"item": {"value": "https://dance.wikibase.cloud/wiki/Q123"}},
                        {"item": {"value": "https://dance.wikibase.cloud/wiki/Q456"}},
                    ]
                }
            }

            client = DancedbClient()
            result = client.search_band("AmbiguousBand")

            assert result is None

    @patch("src.models.dancedb.client.Login")
    def test_search_band_returns_none_on_exception(self, mock_login):
        mock_login.return_value = MagicMock()

        with patch("src.models.dancedb.client.execute_sparql_query") as mock_sparql:
            mock_sparql.side_effect = Exception("SPARQL error")

            client = DancedbClient()
            result = client.search_band("ErrorBand")

            assert result is None


class TestDancedbClientCreateBand:
    @patch("src.models.dancedb.client.Login")
    @patch("src.models.dancedb.client.questionary")
    def test_create_band_user_confirms(self, mock_questionary, mock_login):
        mock_login.return_value = MagicMock()
        mock_questionary.rawselect.return_value.ask.return_value = "Yes (Recommended)"

        client = DancedbClient()

        mock_wbi = MagicMock()
        mock_new_item = MagicMock()
        mock_new_item.id = "Q999"
        mock_wbi.item.new.return_value = mock_new_item
        client.wbi = mock_wbi

        result = client.create_band("NewBand")

        assert result == "Q999"
        mock_new_item.labels.set.assert_called()
        mock_new_item.claims.add.assert_called()
        mock_new_item.write.assert_called_once()

    @patch("src.models.dancedb.client.Login")
    @patch("src.models.dancedb.client.questionary")
    def test_create_band_user_declines(self, mock_questionary, mock_login):
        mock_login.return_value = MagicMock()
        mock_questionary.rawselect.return_value.ask.return_value = "No"

        client = DancedbClient()

        with pytest.raises(Exception) as exc_info:
            client.create_band("DeclinedBand")

        assert "User declined" in str(exc_info.value)

    @patch("src.models.dancedb.client.Login")
    @patch("src.models.dancedb.client.questionary")
    def test_create_band_handles_wbi_exception(self, mock_questionary, mock_login):
        mock_login.return_value = MagicMock()
        mock_questionary.rawselect.return_value.ask.return_value = "Yes (Recommended)"

        client = DancedbClient()

        mock_wbi = MagicMock()
        mock_new_item = MagicMock()
        mock_wbi.item.new.return_value = mock_new_item
        mock_new_item.write.side_effect = Exception("WBI error")
        client.wbi = mock_wbi

        with pytest.raises(Exception) as exc_info:
            client.create_band("ErrorBand")

        assert "WBI error" in str(exc_info.value)


class TestDancedbClientGetOrCreateBand:
    @patch("src.models.dancedb.client.Login")
    def test_get_or_create_returns_existing_band(self, mock_login):
        mock_login.return_value = MagicMock()

        with patch.object(DancedbClient, "search_band", return_value="Q123") as mock_search:
            client = DancedbClient()
            result = client.get_or_create_band("ExistingBand")

            assert result == "Q123"
            mock_search.assert_called_once_with("ExistingBand")

    @patch("src.models.dancedb.client.Login")
    @patch("src.models.dancedb.client.questionary")
    def test_get_or_create_creates_new_band(self, mock_questionary, mock_login):
        mock_login.return_value = MagicMock()
        mock_questionary.rawselect.return_value.ask.return_value = "Yes (Recommended)"

        with patch.object(DancedbClient, "search_band", return_value=None) as mock_search:
            with patch.object(DancedbClient, "create_band", return_value="Q999") as mock_create:
                client = DancedbClient()
                result = client.get_or_create_band("NewBand")

                assert result == "Q999"
                mock_search.assert_called_once_with("NewBand")
                mock_create.assert_called_once_with("NewBand", "")
