import pytest
from unittest.mock import patch, MagicMock

from src.models.cogwork.enums import EventType
from src.models.cogwork.event import CogworkEvent


class TestEvent(CogworkEvent):
    organizer_slug: str = "test"
    organizer_qid: str = "Q1"
    meeting_labels: list[str] = ["årsmöte", "möte", "annual meeting"]
    venue_qid_map: dict[str, str] = {}
    event_url: str = "https://example.com/event/123"


class TestEventType:
    def test_event_type_enum_values(self):
        assert EventType.DANCE.value == "dance"
        assert EventType.MEETING.value == "meeting"
        assert EventType.UNKNOWN.value == "unknown"

    def test_event_type_is_string_enum(self):
        assert isinstance(EventType.DANCE, str)
        assert EventType.DANCE == "dance"


class TestCleanText:
    def test_clean_text_removes_nbsp(self):
        result = CogworkEvent.clean_text("Hello\xa0World")
        assert result == "Hello World"

    def test_clean_text_strips_whitespace(self):
        result = CogworkEvent.clean_text("  Hello World  ")
        assert result == "Hello World"

    def test_clean_text_returns_empty_for_none(self):
        result = CogworkEvent.clean_text(None)
        assert result == ""


class TestEventId:
    def test_event_id_extracts_from_url(self):
        event = TestEvent.model_construct()
        assert event.event_id == "123"


class TestMapVenueQid:
    def test_map_venue_qid_finds_match_case_insensitive(self):
        event = TestEvent.model_construct()
        event.venue_qid_map = {"Test Venue": "Q99"}
        result = event.map_venue_qid("at test venue")
        assert result == "Q99"

    def test_map_venue_qid_returns_empty_when_no_match(self):
        event = TestEvent.model_construct()
        event.venue_qid_map = {"Test Venue": "Q99"}
        result = event.map_venue_qid("unknown place")
        assert result == ""


class TestMapDanceStyleQids:
    def test_map_dance_style_qids_adds_qid(self):
        event = TestEvent.model_construct()
        event.dance_style_qid_map = {"fox": "Q23"}
        event.dance_styles_qids = set()
        event.map_dance_style_qids("Let's dance fox")
        assert "Q23" in event.dance_styles_qids

    def test_map_dance_style_qids_is_case_insensitive(self):
        event = TestEvent.model_construct()
        event.dance_style_qid_map = {"fox": "Q23"}
        event.dance_styles_qids = set()
        event.map_dance_style_qids("Dancing FOX")
        assert "Q23" in event.dance_styles_qids


class TestDetermineSkip:
    def test_skip_when_label_matches(self):
        event = TestEvent.model_construct()
        event.skip_sv_labels = ["test skip"]
        event.event_metadata = {"label_sv": "This is a test skip event"}
        event.determine_skip()
        assert event.skip is True

    def test_no_skip_when_label_doesnt_match(self):
        event = TestEvent.model_construct()
        event.skip_sv_labels = ["test skip"]
        event.event_metadata = {"label_sv": "Normal dance event"}
        event.determine_skip()
        assert event.skip is False


class TestDetermineFull:
    def test_full_mapping_matches_fullt(self):
        event = TestEvent.model_construct()
        event.event_metadata = {"label_sv": "FULLT Dance Event"}
        event.determine_full()
        assert event.full is True

    def test_full_mapping_matches_fullbokad(self):
        event = TestEvent.model_construct()
        event.event_metadata = {"label_sv": "FULLBOKAD Event"}
        event.determine_full()
        assert event.full is True


class TestDetermineEventType:
    def test_detects_årsmöte_case_insensitive(self):
        event = TestEvent.model_construct()
        event.event_metadata = {"label_sv": "ÅRSMÖTE 2024"}
        event.determine_event_type()
        assert event.event_type == EventType.MEETING

    def test_detects_möte_case_insensitive(self):
        event = TestEvent.model_construct()
        event.event_metadata = {"label_sv": "Möte om dans"}
        event.determine_event_type()
        assert event.event_type == EventType.MEETING

    def test_detects_annual_meeting_case_insensitive(self):
        event = TestEvent.model_construct()
        event.event_metadata = {"label_sv": "ANNUAL MEETING"}
        event.determine_event_type()
        assert event.event_type == EventType.MEETING

    def test_dance_event_not_matching(self):
        event = TestEvent.model_construct()
        event.event_metadata = {"label_sv": "Fox danskväll"}
        event.determine_event_type()
        assert event.event_type == EventType.DANCE

    def test_empty_label_defaults_to_dance(self):
        event = TestEvent.model_construct()
        event.event_metadata = {"label_sv": ""}
        event.determine_event_type()
        assert event.event_type == EventType.DANCE

    def test_missing_label_defaults_to_dance(self):
        event = TestEvent.model_construct()
        event.event_metadata = {}
        event.determine_event_type()
        assert event.event_type == EventType.DANCE


class TestParseIntoDanceEventSkip:
    @patch.object(CogworkEvent, "fetch_ical")
    @patch("click.confirm")
    def test_skips_when_venue_qid_not_found(self, mock_confirm, mock_fetch_ical):
        mock_fetch_ical.return_value = "DTSTART:20270120T100000\nDTEND:20270120T120000\nLOCATION:Test\nDESCRIPTION:Test desc"
        mock_confirm.return_value = True
        event = TestEvent.model_construct()
        event.event_metadata = {
            "label_sv": "Test Event",
            "ical_url": "https://example.com/ical"
        }
        event.event_type = EventType.DANCE
        event.parse_into_dance_event()
        assert event.skip is True
        assert event.dance_event is None

    @patch.object(CogworkEvent, "fetch_ical")
    @patch("click.confirm")
    def test_raises_when_venue_qid_not_found_and_user_declines_skip(self, mock_confirm, mock_fetch_ical):
        mock_fetch_ical.return_value = "DTSTART:20270120T100000\nDTEND:20270120T120000\nLOCATION:Test\nDESCRIPTION:Test desc"
        mock_confirm.return_value = False
        event = TestEvent.model_construct()
        event.event_metadata = {
            "label_sv": "Test Event",
            "ical_url": "https://example.com/ical"
        }
        event.event_type = EventType.DANCE
        with pytest.raises(Exception, match="Could not map venue QID"):
            event.parse_into_dance_event()

    @patch.object(CogworkEvent, "fetch_ical")
    @patch("click.prompt")
    def test_user_selects_dance_style_when_not_found(self, mock_prompt, mock_fetch_ical):
        mock_fetch_ical.return_value = "DTSTART:20270120T100000\nDTEND:20270120T120000\nLOCATION:Test\nDESCRIPTION:Test desc"
        mock_prompt.return_value = "fox"
        event = TestEvent.model_construct()
        event.venue_qid_map = {"Test": "Q99"}
        event.dance_style_qid_map = {"fox": "Q23", "bugg": "Q485"}
        event.event_metadata = {
            "label_sv": "Test Event",
            "ical_url": "https://example.com/ical"
        }
        event.event_type = EventType.DANCE
        event.parse_into_dance_event()
        assert event.skip is False
        assert event.dance_event is not None
        assert "Q23" in event.dance_styles_qids

    @patch.object(CogworkEvent, "fetch_ical")
    @patch("click.prompt")
    def test_defaults_to_socialdans_when_style_not_found(self, mock_prompt, mock_fetch_ical):
        mock_fetch_ical.return_value = "DTSTART:20270120T100000\nDTEND:20270120T120000\nLOCATION:Test\nDESCRIPTION:Test desc"
        mock_prompt.return_value = "socialdans"
        event = TestEvent.model_construct()
        event.venue_qid_map = {"Test": "Q99"}
        event.dance_style_qid_map = {"fox": "Q23", "socialdans": "Q4"}
        event.event_metadata = {
            "label_sv": "Test Event",
            "ical_url": "https://example.com/ical"
        }
        event.event_type = EventType.DANCE
        event.parse_into_dance_event()
        assert event.skip is False
        assert event.dance_event is not None
        assert "Q4" in event.dance_styles_qids

    @patch.object(CogworkEvent, "fetch_ical")
    def test_succeeds_when_venue_and_style_found(self, mock_fetch_ical):
        mock_fetch_ical.return_value = "DTSTART:20270120T100000\nDTEND:20270120T120000\nLOCATION:Test\nDESCRIPTION:Test desc"
        event = TestEvent.model_construct()
        event.venue_qid_map = {"Test": "Q99"}
        event.dance_style_qid_map = {"Test": "Q23"}
        event.event_metadata = {
            "label_sv": "Fox Event",
            "ical_url": "https://example.com/ical"
        }
        event.event_type = EventType.DANCE
        event.parse_into_dance_event()
        assert event.skip is False
        assert event.dance_event is not None
        assert event.dance_event.event_type == "dance"

    @patch.object(CogworkEvent, "fetch_ical")
    def test_event_type_meeting_in_output(self, mock_fetch_ical):
        mock_fetch_ical.return_value = "DTSTART:20270120T100000\nDTEND:20270120T120000\nLOCATION:Test\nDESCRIPTION:Test desc"
        event = TestEvent.model_construct()
        event.venue_qid_map = {"Test": "Q99"}
        event.dance_style_qid_map = {"Test": "Q23"}
        event.event_metadata = {
            "label_sv": "Årsmöte 2024",
            "ical_url": "https://example.com/ical"
        }
        event.event_type = EventType.MEETING
        event.parse_into_dance_event()
        assert event.skip is False
        assert event.dance_event is not None
        assert event.dance_event.event_type == "meeting"

    @patch.object(CogworkEvent, "fetch_ical")
    def test_raises_when_no_ical_url(self, mock_fetch_ical):
        mock_fetch_ical.return_value = ""
        event = TestEvent.model_construct()
        event.event_metadata = {
            "label_sv": "Test Event",
            "ical_url": None
        }
        event.event_type = EventType.DANCE
        with pytest.raises(Exception, match="No ical URL found"):
            event.parse_into_dance_event()


class TestFetchAndParse:
    @patch.object(CogworkEvent, "fetch_event_page")
    @patch.object(CogworkEvent, "extract_event_metadata")
    @patch.object(CogworkEvent, "parse_shop_page")
    @patch.object(CogworkEvent, "parse_into_dance_event")
    def test_fetch_and_parse_skips_when_skip_true(
        self, mock_parse, mock_shop, mock_extract, mock_fetch
    ):
        event = TestEvent.model_construct()
        event.event_metadata = {"label_sv": "Skip me"}
        event.skip_sv_labels = ["Skip me"]
        event.fetch_and_parse()
        mock_parse.assert_not_called()
        mock_shop.assert_not_called()


class TestParsePrice:
    @patch.object(CogworkEvent, "fetch_shop_page")
    def test_parse_price_from_swedish_format(self, mock_fetch):
        mock_fetch.return_value = None
        event = TestEvent.model_construct()
        event.shop_html = "<p>Kursen kostar 500 kr</p>"
        event.parse_price()
        assert event.price_normal == 500

    @patch.object(CogworkEvent, "fetch_shop_page")
    def test_parse_price_from_swedish_format_no_space(self, mock_fetch):
        mock_fetch.return_value = None
        event = TestEvent.model_construct()
        event.shop_html = "<p>Kursen kostar 500kr</p>"
        event.parse_price()
        assert event.price_normal == 500

    @patch.object(CogworkEvent, "fetch_shop_page")
    def test_parse_price_from_swedish_format_case_insensitive(self, mock_fetch):
        mock_fetch.return_value = None
        event = TestEvent.model_construct()
        event.shop_html = "<p>KOSTAR 750 KR</p>"
        event.parse_price()
        assert event.price_normal == 750

    @patch.object(CogworkEvent, "fetch_shop_page")
    def test_parse_price_from_ovriga_format(self, mock_fetch):
        mock_fetch.return_value = None
        event = TestEvent.model_construct()
        event.shop_html = "<p>Avgift: Studerande, pensionär 300.-, övriga 500.-</p>"
        event.parse_price()
        assert event.price_normal == 500

    @patch.object(CogworkEvent, "fetch_shop_page")
    def test_parse_price_from_kostar_with_student_price(self, mock_fetch):
        mock_fetch.return_value = None
        event = TestEvent.model_construct()
        event.shop_html = "<p>Kursen kostar 400 kr för 6 tillfällen (studerande eller pensionär 250 kr)</p>"
        event.parse_price()
        assert event.price_normal == 400
