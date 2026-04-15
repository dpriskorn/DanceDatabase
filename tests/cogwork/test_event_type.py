from unittest.mock import patch

import pytest

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


class TestMapVenueQidEdge:
    def test_parse_ical_text_basic(self):
        event = TestEvent.model_construct()
        ical = "DTSTART:20270120T100000\nDTEND:20270120T120000\nLOCATION:Test Hall\nDESCRIPTION:Test event"
        event.parse_ical_text(ical)
        assert event.start_time is not None
        assert event.end_time is not None
        assert event.location == "Test Hall"

    def test_parse_ical_text_no_dtend(self):
        event = TestEvent.model_construct()
        ical = "DTSTART:20270120T100000\nLOCATION:Test Hall"
        event.parse_ical_text(ical)
        assert event.start_time is not None


class TestParseOccasions:
    def test_parse_occasions_found(self):
        event = TestEvent.model_construct()
        event.shop_html = "<p><b>Occasions</b>: 5</p>"
        event.parse_occasions()
        assert event.occasions == 5

    def test_parse_occasions_not_found(self):
        event = TestEvent.model_construct()
        event.shop_html = "<div>No occasions</div>"
        with pytest.raises(Exception, match="No occasions found"):
            event.parse_occasions()

    @patch.object(CogworkEvent, "fetch_shop_page")
    def test_parse_occasions_fetches_html_if_needed(self, mock_fetch):
        mock_fetch.return_value = None
        event = TestEvent.model_construct()
        event.shop_html = ""
        event.shop_html = "<p><b>Occasions</b>: 3</p>"
        event.parse_occasions()
        assert event.occasions == 3

    @patch.object(CogworkEvent, "fetch_shop_page")
    def test_parse_price_fetches_html_if_needed(self, mock_fetch):
        mock_fetch.return_value = None
        event = TestEvent.model_construct()
        event.shop_html = ""
        event.shop_html = "<p><b>Avgift</b>: 200 kr</p>"
        event.parse_price()
        assert event.price_normal == 200
