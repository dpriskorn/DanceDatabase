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
        event.price_normal = 0
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
        event.price_normal = 0
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
        event.price_normal = 0
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
        event.price_normal = 0
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

    @patch.object(CogworkEvent, "fetch_event_page")
    @patch.object(CogworkEvent, "extract_event_metadata")
    @patch.object(CogworkEvent, "determine_event_type")
    @patch.object(CogworkEvent, "determine_skip")
    @patch.object(CogworkEvent, "determine_full")
    @patch.object(CogworkEvent, "parse_shop_page")
    @patch.object(CogworkEvent, "parse_into_dance_event")
    def test_fetch_and_parse_calls_full_workflow(
        self, mock_parse, mock_shop, mock_full, mock_skip, mock_type, mock_extract, mock_fetch
    ):
        event = TestEvent.model_construct()
        event.event_metadata = {"label_sv": "Test Event", "ical_url": "http://test.ical"}
        event.skip = False
        event.skip_sv_labels = []
        event.event_type = EventType.DANCE
        event.fetch_and_parse()
        mock_full.assert_called_once()
        mock_shop.assert_called_once()
        mock_parse.assert_called_once()


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

    @patch.object(CogworkEvent, "fetch_shop_page")
    def test_parse_price_with_nbsp(self, mock_fetch):
        mock_fetch.return_value = None
        event = TestEvent.model_construct()
        event.shop_html = "<p>Kursen kostar 400\xa0kr för 6 tillfällen</p>"
        event.parse_price()
        assert event.price_normal == 400

    @patch.object(CogworkEvent, "fetch_shop_page")
    def test_parse_price_falls_through_to_ovriga(self, mock_fetch):
        mock_fetch.return_value = None
        event = TestEvent.model_construct()
        event.shop_html = '<b>Price</b>: <span>0</span> Avgift: Studerande, pensionär 300.-, övriga 500.-'
        event.parse_price()
        assert event.price_normal == 500

    @patch.object(CogworkEvent, "fetch_shop_page")
    def test_parse_price_from_avgift_bold_tag(self, mock_fetch):
        mock_fetch.return_value = None
        event = TestEvent.model_construct()
        event.shop_html = '<p><b>Avgift</b>: 550 kr</p>'
        event.parse_price()
        assert event.price_normal == 550


class TestFetchEventPage:
    @patch("requests.get")
    def test_fetch_event_page_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = "<html><h1>Test Event</h1></html>"
        mock_get.return_value = mock_response
        event = TestEvent.model_construct()
        event.fetch_event_page()
        assert event.event_html == "<html><h1>Test Event</h1></html>"

    @patch("requests.get")
    def test_fetch_event_page_raises_on_error(self, mock_get):
        mock_get.return_value.raise_for_status.side_effect = Exception("HTTP Error")
        event = TestEvent.model_construct()
        with pytest.raises(Exception, match="HTTP Error"):
            event.fetch_event_page()


class TestExtractEventMetadata:
    def test_extract_event_metadata_without_h1(self):
        event = TestEvent.model_construct()
        event.event_html = "<html><div>No h1</div></html>"
        event.extract_event_metadata()
        assert event.event_metadata["label_sv"] == ""

    def test_extract_event_metadata_without_ical_link(self):
        event = TestEvent.model_construct()
        event.event_html = "<html><h1>Test Event</h1></html>"
        event.extract_event_metadata()
        assert event.event_metadata["ical_url"] is None

    def test_extract_event_metadata_raises_without_html(self):
        event = TestEvent.model_construct()
        event.event_html = ""
        with pytest.raises(Exception, match="no event_html"):
            event.extract_event_metadata()


class TestDetermineFull:
    def test_full_false_when_label_empty(self):
        event = TestEvent.model_construct()
        event.event_metadata = {"label_sv": ""}
        event.determine_full()
        assert event.full is False

    def test_full_false_for_regular_event(self):
        event = TestEvent.model_construct()
        event.event_metadata = {"label_sv": "Danskväll med liveband"}
        event.determine_full()
        assert event.full is False


class TestFetchShopPage:
    @patch("requests.get")
    def test_fetch_shop_page_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = "<html><b>Price</b>: 300</html>"
        mock_get.return_value = mock_response
        event = TestEvent.model_construct()
        event.fetch_shop_page()
        assert event.shop_html is not None


class TestFetchIcal:
    @patch("requests.get")
    def test_fetch_ical_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = "DTSTART:20270120T100000"
        mock_get.return_value = mock_response
        event = TestEvent.model_construct()
        result = event.fetch_ical("https://example.com/ical")
        assert "DTSTART" in result

    @patch("requests.get")
    def test_fetch_ical_raises_on_error(self, mock_get):
        mock_get.return_value.raise_for_status.side_effect = Exception("HTTP Error")
        event = TestEvent.model_construct()
        with pytest.raises(Exception, match="HTTP Error"):
            event.fetch_ical("https://example.com/ical")


class TestCheckRegistration:
    @patch.object(CogworkEvent, "fetch_shop_page")
    def test_check_registration_open(self, mock_fetch):
        mock_fetch.return_value = None
        event = TestEvent.model_construct()
        event.shop_html = '<input value="Book »">'
        event.check_registration()
        assert event.registration_open is True

    @patch.object(CogworkEvent, "fetch_shop_page")
    def test_check_registration_closed(self, mock_fetch):
        mock_fetch.return_value = None
        event = TestEvent.model_construct()
        event.shop_html = '<input value="Something else">'
        event.check_registration()
        assert event.registration_open is False


class TestParsePlace:
    def test_parse_place_found(self):
        event = TestEvent.model_construct()
        event.shop_html = '<p class="cwPlace">Test Venue</p>'
        event.parse_place()
        assert event.place == "Test Venue"

    def test_parse_place_not_found(self):
        event = TestEvent.model_construct()
        event.shop_html = '<div>No place</div>'
        event.parse_place()
        assert event.place == ""

    @patch.object(CogworkEvent, "fetch_shop_page")
    def test_parse_place_fetches_if_needed(self, mock_fetch):
        mock_fetch.return_value = None
        event = TestEvent.model_construct()
        event.shop_html = ""
        event.parse_place()
        mock_fetch.assert_called_once()


class TestDetermineFullEdgeCases:
    def test_full_false_for_empty_label(self):
        event = TestEvent.model_construct()
        event.event_metadata = {"label_sv": ""}
        event.determine_full()
        assert event.full is False

    def test_full_true_for_fullbokad(self):
        event = TestEvent.model_construct()
        event.event_metadata = {"label_sv": "FULLBOKAD"}
        event.determine_full()
        assert event.full is True


class TestShopUrl:
    def test_shop_url_format(self):
        event = TestEvent.model_construct()
        url = event.shop_url
        assert "dans.se" in url
        assert "test" in url
        assert "event=123" in url


class TestMapVenueQid:
    def test_map_venue_qid_case_insensitive(self):
        event = TestEvent.model_construct()
        event.venue_qid_map = {"Test Venue": "Q99"}
        result = event.map_venue_qid("TEST VENUE in Stockholm")
        assert result == "Q99"

    def test_map_venue_qid_not_found(self):
        event = TestEvent.model_construct()
        event.venue_qid_map = {"Test Venue": "Q99"}
        result = event.map_venue_qid("Unknown Place")
        assert result == ""


class TestMapDanceStyleQids:
    def test_map_dance_style_qids_multiple(self):
        event = TestEvent.model_construct()
        event.dance_style_qid_map = {"fox": "Q23", "bugg": "Q485"}
        event.dance_styles_qids = set()
        event.map_dance_style_qids("Fox and Bugg dancing")
        assert "Q23" in event.dance_styles_qids
        assert "Q485" in event.dance_styles_qids

    def test_map_dance_style_qids_none_found(self):
        event = TestEvent.model_construct()
        event.dance_style_qid_map = {"fox": "Q23"}
        event.dance_styles_qids = set()
        event.map_dance_style_qids("No dance style here")
        assert len(event.dance_styles_qids) == 0


class TestCleanText:
    def test_clean_text_normalizes_whitespace(self):
        result = CogworkEvent.clean_text("  Hello   World  ")
        assert result == "Hello   World"

    def test_clean_text_removes_nbsp(self):
        result = CogworkEvent.clean_text("Hello\xa0World")
        assert result == "Hello World"

    def test_clean_text_handles_none(self):
        result = CogworkEvent.clean_text(None)
        assert result == ""


class TestEventId:
    def test_event_id_from_url(self):
        event = TestEvent.model_construct()
        assert event.event_id == "123"


class TestParseRegistrationDatetime:
    def test_parse_registration_datetime_found(self):
        event = TestEvent.model_construct()
        event.shop_html = '<div class="cwRegStatus">Registration opens mon. 13/10 19:00</div>'
        event.parse_registration_datetime()
        assert event.registration_opens is not None

    def test_parse_registration_datetime_not_found(self):
        event = TestEvent.model_construct()
        event.shop_html = '<div class="cwRegStatus">No opening info</div>'
        event.parse_registration_datetime()
        assert event.registration_opens is None

    @patch.object(CogworkEvent, "fetch_shop_page")
    def test_parse_registration_datetime_fetches_html_if_needed(self, mock_fetch):
        mock_fetch.return_value = None
        event = TestEvent.model_construct()
        event.shop_html = ""
        event.parse_registration_datetime()
        mock_fetch.assert_called_once()


class TestCheckRegistrationEdgeCases:
    @patch.object(CogworkEvent, "fetch_shop_page")
    def test_check_registration_fetches_html_if_needed(self, mock_fetch):
        mock_fetch.return_value = None
        event = TestEvent.model_construct()
        event.shop_html = ""
        event.check_registration()
        mock_fetch.assert_called_once()


class TestParseIcalTextEdgeCases:
    def test_parse_ical_text_invalid_dtstart_format(self):
        event = TestEvent.model_construct()
        ical = "DTSTART:invalid\nDTEND:20270120T120000\nLOCATION:Test"
        event.parse_ical_text(ical)
        assert event.start_time is None
        assert event.end_time is not None

    def test_parse_ical_text_no_dtstart(self):
        event = TestEvent.model_construct()
        ical = "DTEND:20270120T120000\nLOCATION:Test"
        event.parse_ical_text(ical)
        assert event.start_time is None


class TestParseRegistrationDatetimeEdgeCases:
    def test_parse_registration_datetime_regex_no_match(self):
        event = TestEvent.model_construct()
        event.shop_html = '<div class="cwRegStatus">Registration opens but no valid date</div>'
        event.parse_registration_datetime()
        assert event.registration_opens is None

    def test_parse_registration_datetime_invalid_date_format(self):
        event = TestEvent.model_construct()
        event.shop_html = '<div class="cwRegStatus">Registration opens 99/99/99 25:00</div>'
        with pytest.raises(Exception, match="Failed to parse datetime"):
            event.parse_registration_datetime()


class TestParseIntoDanceEventFull:
    @patch.object(CogworkEvent, "fetch_ical")
    @patch("click.prompt")
    @patch("click.confirm")
    def test_parse_into_dance_event_with_style_selection(
        self, mock_confirm, mock_prompt, mock_fetch_ical
    ):
        mock_fetch_ical.return_value = "DTSTART:20270120T100000\nDTEND:20270120T120000\nLOCATION:Test\nDESCRIPTION:Test desc"
        mock_confirm.return_value = True
        mock_prompt.return_value = "fox"
        event = TestEvent.model_construct()
        event.venue_qid_map = {"Test": "Q99"}
        event.dance_style_qid_map = {"fox": "Q23"}
        event.event_metadata = {
            "label_sv": "Test Event",
            "ical_url": "https://example.com/ical"
        }
        event.event_type = EventType.DANCE
        event.price_normal = 0
        event.parse_into_dance_event()
        assert event.skip is False
        assert event.dance_event is not None


class TestMapVenueQidEdge:
    def test_map_venue_qid_empty_map(self):
        event = TestEvent.model_construct()
        event.venue_qid_map = {}
        result = event.map_venue_qid("Any place")
        assert result == ""


class TestParseIcalText:
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
        event.shop_html = '<p><b>Occasions</b>: 5</p>'
        event.parse_occasions()
        assert event.occasions == 5

    def test_parse_occasions_not_found(self):
        event = TestEvent.model_construct()
        event.shop_html = '<div>No occasions</div>'
        with pytest.raises(Exception, match="No occasions found"):
            event.parse_occasions()

    @patch.object(CogworkEvent, "fetch_shop_page")
    def test_parse_occasions_fetches_html_if_needed(self, mock_fetch):
        mock_fetch.return_value = None
        event = TestEvent.model_construct()
        event.shop_html = ""
        event.shop_html = '<p><b>Occasions</b>: 3</p>'
        event.parse_occasions()
        assert event.occasions == 3

    @patch.object(CogworkEvent, "fetch_shop_page")
    def test_parse_price_fetches_html_if_needed(self, mock_fetch):
        mock_fetch.return_value = None
        event = TestEvent.model_construct()
        event.shop_html = ""
        event.shop_html = '<p><b>Avgift</b>: 200 kr</p>'
        event.parse_price()
        assert event.price_normal == 200
