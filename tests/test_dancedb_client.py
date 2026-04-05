import click
import pytest
from unittest.mock import MagicMock, patch

from src.models.dancedb_client import DancedbClient


class TestDancedbClientSearchBand:
    @patch('src.models.dancedb_client.Login')
    def test_search_band_finds_single_match(self, mock_login):
        mock_login.return_value = MagicMock()

        with patch('src.models.dancedb_client.execute_sparql_query') as mock_sparql:
            mock_sparql.return_value = {
                'results': {
                    'bindings': [
                        {'item': {'value': 'https://dance.wikibase.cloud/wiki/Q123'}}
                    ]
                }
            }

            client = DancedbClient()
            result = client.search_band('TestBand')

            assert result == 'Q123'
            mock_sparql.assert_called_once()

    @patch('src.models.dancedb_client.Login')
    def test_search_band_returns_none_when_no_match(self, mock_login):
        mock_login.return_value = MagicMock()

        with patch('src.models.dancedb_client.execute_sparql_query') as mock_sparql:
            mock_sparql.return_value = {'results': {'bindings': []}}

            client = DancedbClient()
            result = client.search_band('UnknownBand')

            assert result is None

    @patch('src.models.dancedb_client.Login')
    def test_search_band_returns_none_when_multiple_matches(self, mock_login):
        mock_login.return_value = MagicMock()

        with patch('src.models.dancedb_client.execute_sparql_query') as mock_sparql:
            mock_sparql.return_value = {
                'results': {
                    'bindings': [
                        {'item': {'value': 'https://dance.wikibase.cloud/wiki/Q123'}},
                        {'item': {'value': 'https://dance.wikibase.cloud/wiki/Q456'}},
                    ]
                }
            }

            client = DancedbClient()
            result = client.search_band('AmbiguousBand')

            assert result is None

    @patch('src.models.dancedb_client.Login')
    def test_search_band_returns_none_on_exception(self, mock_login):
        mock_login.return_value = MagicMock()

        with patch('src.models.dancedb_client.execute_sparql_query') as mock_sparql:
            mock_sparql.side_effect = Exception('SPARQL error')

            client = DancedbClient()
            result = client.search_band('ErrorBand')

            assert result is None


class TestDancedbClientCreateBand:
    @patch('src.models.dancedb_client.Login')
    @patch('src.models.dancedb_client.wbi_helpers')
    @patch('src.models.dancedb_client.click')
    def test_create_band_user_confirms(self, mock_click, mock_wbi_helpers, mock_login):
        mock_login.return_value = MagicMock()
        mock_click.confirm.return_value = True

        mock_new_item = MagicMock()
        mock_new_item.id = 'Q999'
        mock_new_item.claims = MagicMock()
        mock_wbi_helpers.create_item.return_value = mock_new_item

        client = DancedbClient()
        result = client.create_band('NewBand')

        assert result == 'Q999'
        mock_wbi_helpers.create_item.assert_called_once()
        mock_new_item.claims.add.assert_called_once_with('P31', 'Q215380')
        mock_new_item.write.assert_called_once()

    @patch('src.models.dancedb_client.Login')
    @patch('src.models.dancedb_client.click')
    def test_create_band_user_declines(self, mock_click, mock_login):
        mock_login.return_value = MagicMock()
        mock_click.confirm.return_value = False
        mock_click.Abort = click.Abort

        client = DancedbClient()

        with pytest.raises(Exception) as exc_info:
            client.create_band('DeclinedBand')

        assert 'User declined' in str(exc_info.value)

    @patch('src.models.dancedb_client.Login')
    @patch('src.models.dancedb_client.wbi_helpers')
    @patch('src.models.dancedb_client.click')
    def test_create_band_ctrl_c_converts_to_keyboard_interrupt(self, mock_click, mock_wbi_helpers, mock_login):
        mock_login.return_value = MagicMock()
        mock_click.confirm.side_effect = click.Abort()
        mock_click.Abort = click.Abort

        client = DancedbClient()

        with pytest.raises(KeyboardInterrupt):
            client.create_band('CtrlCBand')

    @patch('src.models.dancedb_client.Login')
    @patch('src.models.dancedb_client.wbi_helpers')
    @patch('src.models.dancedb_client.click')
    def test_create_band_handles_wbi_exception(self, mock_click, mock_wbi_helpers, mock_login):
        mock_login.return_value = MagicMock()
        mock_click.confirm.return_value = True
        mock_wbi_helpers.create_item.side_effect = Exception('WBI error')

        client = DancedbClient()

        with pytest.raises(Exception) as exc_info:
            client.create_band('ErrorBand')

        assert 'WBI error' in str(exc_info.value)


class TestDancedbClientGetOrCreateBand:
    @patch('src.models.dancedb_client.Login')
    def test_get_or_create_returns_existing_band(self, mock_login):
        mock_login.return_value = MagicMock()

        with patch.object(DancedbClient, 'search_band', return_value='Q123') as mock_search:
            client = DancedbClient()
            result = client.get_or_create_band('ExistingBand')

            assert result == 'Q123'
            mock_search.assert_called_once_with('ExistingBand')

    @patch('src.models.dancedb_client.Login')
    @patch('src.models.dancedb_client.click')
    def test_get_or_create_creates_new_band(self, mock_click, mock_login):
        mock_login.return_value = MagicMock()
        mock_click.confirm.return_value = True

        with patch.object(DancedbClient, 'search_band', return_value=None) as mock_search:
            with patch.object(DancedbClient, 'create_band', return_value='Q999') as mock_create:
                client = DancedbClient()
                result = client.get_or_create_band('NewBand')

                assert result == 'Q999'
                mock_search.assert_called_once_with('NewBand')
                mock_create.assert_called_once_with('NewBand')