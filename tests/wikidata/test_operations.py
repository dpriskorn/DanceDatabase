import json
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestScrapeWikidataArtists:
    @patch("wikibaseintegrator.wbi_helpers.execute_sparql_query")
    @patch("src.models.wikidata.operations.root_config")
    def test_scrape_wikidata_artists(self, mock_root_config, mock_execute_sparql_query):
        from src.models.wikidata.operations import scrape_wikidata_artists

        mock_root_config.user_agent = "DanceDB/1.0 (User:So9q)"
        mock_root_config.wikidata_dir = Path("/tmp/wikidata_test")

        mock_execute_sparql_query.return_value = {
            "results": {
                "bindings": [
                    {"o": {"value": "https://www.wikidata.org/entity/Q123"}, "oLabel": {"value": "Test Artist"}},
                    {"o": {"value": "https://www.wikidata.org/entity/Q456"}, "oLabel": {"value": "Another Artist"}},
                ]
            }
        }

        scrape_wikidata_artists("2026-01-01")

        mock_execute_sparql_query.assert_called_once()
        call_args = mock_execute_sparql_query.call_args
        assert "LIMIT 5000" in call_args.kwargs["query"]

        output_file = Path("/tmp/wikidata_test/artists/2026-01-01.json")
        assert output_file.exists()

        data = json.loads(output_file.read_text())
        assert "Q123" in data
        assert data["Q123"]["label"] == "Test Artist"

    @patch("wikibaseintegrator.wbi_helpers.execute_sparql_query")
    @patch("src.models.wikidata.operations.root_config")
    def test_saves_to_correct_path(self, mock_root_config, mock_execute_sparql_query):
        from src.models.wikidata.operations import scrape_wikidata_artists

        mock_root_config.user_agent = "DanceDB/1.0 (User:So9q)"
        mock_root_config.wikidata_dir = Path("/tmp/wikidata_test2")

        mock_execute_sparql_query.return_value = {"results": {"bindings": []}}

        scrape_wikidata_artists("2026-04-14")

        output_file = Path("/tmp/wikidata_test2/artists/2026-04-14.json")
        assert output_file.exists()


class TestMatchWikidataArtists:
    @patch("src.models.wikidata.operations.DancedbClient")
    @patch("src.models.wikidata.operations.root_config")
    def test_match_wikidata_artists_loads_files(self, mock_root_config, MockDancedbClient):
        from src.models.wikidata.operations import match_wikidata_artists

        mock_root_config.wikidata_dir = Path("/tmp/wikidata_match_test3")

        wd_file = Path("/tmp/wikidata_match_test3/artists/2026-01-03.json")
        wd_file.parent.mkdir(parents=True, exist_ok=True)
        wd_file.write_text(json.dumps({"Q123": {"label": "Test Band"}, "Q456": {"label": "Another Band"}}))

        mock_client = MagicMock()
        mock_client.fetch_artists_from_dancedb.return_value = []
        mock_client.wbi = MagicMock()
        mock_client.wbi.item = MagicMock()
        mock_client.wbi.login = MagicMock()
        mock_client.base_url = "https://dance.wikibase.cloud"
        MockDancedbClient.return_value = mock_client

        match_wikidata_artists("2026-01-03", dry_run=True)

        mock_client.fetch_artists_from_dancedb.assert_called_once()

    @patch("src.models.wikidata.operations.DancedbClient")
    @patch("src.models.wikidata.operations.root_config")
    def test_match_wikidata_artists_dry_run(self, mock_root_config, MockDancedbClient):
        from src.models.wikidata.operations import match_wikidata_artists

        mock_root_config.wikidata_dir = Path("/tmp/wikidata_match_test4")

        wd_file = Path("/tmp/wikidata_match_test4/artists/2026-01-04.json")
        wd_file.parent.mkdir(parents=True, exist_ok=True)
        wd_file.write_text(json.dumps({"Q999": {"label": "Known Band"}}))

        mock_client = MagicMock()
        mock_client.fetch_artists_from_dancedb.return_value = [
            {"qid": "Q227", "label": "Known Band", "aliases": []},
        ]
        mock_client.wbi = MagicMock()
        mock_client.wbi.item = MagicMock()
        mock_client.wbi.login = MagicMock()
        mock_client.base_url = "https://dance.wikibase.cloud"
        MockDancedbClient.return_value = mock_client

        match_wikidata_artists("2026-01-04", dry_run=True)

        mock_client.wbi.item.get.assert_not_called()

    @patch("src.models.wikidata.operations.DancedbClient")
    @patch("src.models.wikidata.operations.root_config")
    def test_match_wikidata_artists_no_file(self, mock_root_config, MockDancedbClient):
        from src.models.wikidata.operations import match_wikidata_artists

        mock_root_config.wikidata_dir = Path("/tmp/wikidata_no_file")

        mock_client = MagicMock()
        MockDancedbClient.return_value = mock_client

        match_wikidata_artists("2026-01-05", dry_run=True)

        mock_client.fetch_artists_from_dancedb.assert_not_called()

    @patch("src.models.wikidata.operations.DancedbClient")
    @patch("src.models.wikidata.operations.root_config")
    def test_match_wikidata_artists_no_matches(self, mock_root_config, MockDancedbClient):
        from src.models.wikidata.operations import match_wikidata_artists

        mock_root_config.wikidata_dir = Path("/tmp/wikidata_no_match")

        wd_file = Path("/tmp/wikidata_no_match/artists/2026-01-06.json")
        wd_file.parent.mkdir(parents=True, exist_ok=True)
        wd_file.write_text(json.dumps({"Q111": {"label": "WD Band"}}))

        mock_client = MagicMock()
        mock_client.fetch_artists_from_dancedb.return_value = [
            {"qid": "Q227", "label": "DB Band", "aliases": []},
        ]
        mock_client.wbi = MagicMock()
        mock_client.wbi.item = MagicMock()
        mock_client.wbi.login = MagicMock()
        mock_client.base_url = "https://dance.wikibase.cloud"
        MockDancedbClient.return_value = mock_client

        with patch("rapidfuzz.process.extractOne", return_value=None):
            match_wikidata_artists("2026-01-06", dry_run=True)

        mock_client.wbi.item.get.assert_not_called()

    @patch("src.models.wikidata.operations.DancedbClient")
    @patch("src.models.wikidata.operations.root_config")
    def test_match_wikidata_artists_uploads(self, mock_root_config, MockDancedbClient):
        from src.models.wikidata.operations import match_wikidata_artists

        mock_root_config.wikidata_dir = Path("/tmp/wikidata_upload")

        wd_file = Path("/tmp/wikidata_upload/artists/2026-01-07.json")
        wd_file.parent.mkdir(parents=True, exist_ok=True)
        wd_file.write_text(json.dumps({"Q999": {"label": "Matched Band"}}))

        mock_item = MagicMock()
        mock_client = MagicMock()
        mock_client.fetch_artists_from_dancedb.return_value = [
            {"qid": "Q227", "label": "Matched Band", "aliases": []},
        ]
        mock_client.wbi = MagicMock()
        mock_client.wbi.item = MagicMock()
        mock_client.wbi.item.get.return_value = mock_item
        mock_client.wbi.login = MagicMock()
        mock_client.base_url = "https://dance.wikibase.cloud"
        MockDancedbClient.return_value = mock_client

        with patch("rapidfuzz.process.extractOne", return_value=None):
            match_wikidata_artists("2026-01-07", dry_run=False)

        mock_client.wbi.item.get.assert_called_once_with(entity_id="Q227")
        mock_item.claims.add.assert_called_once()
        mock_item.write.assert_called_once()


class TestSyncWikidataArtists:
    @patch("src.models.wikidata.operations.DancedbClient")
    @patch("src.models.wikidata.operations.root_config")
    def test_sync_wikidata_artists_uses_band_map(self, mock_root_config, MockDancedbClient):
        from src.models.wikidata.operations import sync_wikidata_artists

        mock_root_config.wikidata_dir = Path("/tmp/wikidata_sync_test")

        wd_file = Path("/tmp/wikidata_sync_test/artists/2026-01-10.json")
        wd_file.parent.mkdir(parents=True, exist_ok=True)
        wd_file.write_text(json.dumps({"Q123": {"label": "Test Band"}}))

        mock_client = MagicMock()
        mock_client.fetch_artists_from_dancedb.return_value = []
        mock_client.wbi = MagicMock()
        mock_client.wbi.item = MagicMock()
        mock_client.wbi.login = MagicMock()
        mock_client.base_url = "https://dance.wikibase.cloud"
        MockDancedbClient.return_value = mock_client

        with patch("src.models.danslogen.data.load_band_map") as mock_load_band_map:
            mock_load_band_map.return_value = {"Test Band": "Q999"}
            sync_wikidata_artists("2026-01-10", dry_run=True)

        mock_client.fetch_artists_from_dancedb.assert_called_once()

    @patch("src.models.wikidata.operations.DancedbClient")
    @patch("src.models.wikidata.operations.root_config")
    def test_sync_wikidata_artists_no_missing(self, mock_root_config, MockDancedbClient):
        from src.models.wikidata.operations import sync_wikidata_artists

        mock_root_config.wikidata_dir = Path("/tmp/wikidata_sync_test2")

        wd_file = Path("/tmp/wikidata_sync_test2/artists/2026-01-11.json")
        wd_file.parent.mkdir(parents=True, exist_ok=True)
        wd_file.write_text(json.dumps({"Q999": {"label": "New Band"}}))

        mock_client = MagicMock()
        mock_client.fetch_artists_from_dancedb.return_value = [
            {"qid": "Q227", "label": "Existing Band", "aliases": []},
        ]
        MockDancedbClient.return_value = mock_client

        with patch("src.models.danslogen.data.load_band_map") as mock_load_band_map:
            mock_load_band_map.return_value = {"Existing Band": "Q227"}
            sync_wikidata_artists("2026-01-11", dry_run=True)

        mock_client.wbi.item.new.assert_not_called()
