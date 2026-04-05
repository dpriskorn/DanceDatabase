import pytest
from unittest.mock import MagicMock, patch

from src.models.onbeat.events import OnbeatEvents


class TestMapCommunityQid:
    def test_maps_known_community(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        assert event.map_community_qid("WCS Umeå") == "Q16"

    def test_maps_salsa_sundsvall(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        assert event.map_community_qid("Salsa Sundsvall") == "Q498"

    def test_returns_empty_for_unknown(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        assert event.map_community_qid("Unknown Community") == ""

    def test_case_insensitive(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        assert event.map_community_qid("wcs umeå") == "Q16"


class TestMapDanceStyleQids:
    def test_maps_fox(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        assert "Q23" in event.map_dance_style_qids("fox")

    def test_maps_wcs(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        assert "Q15" in event.map_dance_style_qids("west coast swing")

    def test_maps_bugg(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        assert "Q485" in event.map_dance_style_qids("bugg")

    def test_returns_empty_for_unknown(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        assert event.map_dance_style_qids("unknown style") == set()

    def test_case_insensitive(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        assert "Q23" in event.map_dance_style_qids("FOX")

    def test_maps_multiple_styles(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        result = event.map_dance_style_qids("fox och bugg")
        assert "Q23" in result
        assert "Q485" in result


class TestMapVenueQid:
    def test_maps_known_venue(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        event.venue_qid_map = {"Test Venue": "Q99"}
        assert event.map_venue_qid("Test Venue") == "Q99"

    def test_returns_empty_for_unknown(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        event.venue_qid_map = {"Test Venue": "Q99"}
        assert event.map_venue_qid("Unknown Place") == ""

    def test_case_insensitive(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        event.venue_qid_map = {"Test Venue": "Q99"}
        assert event.map_venue_qid("test venue") == "Q99"


class TestParseCommunityName:
    def test_parses_known_community(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/wcs-umea")
        event.soup = MagicMock()
        header = MagicMock()
        header.get_text.return_value = "WCS Umeå"
        event.soup.select_one.return_value = header
        event.parse_community_name()
        assert event.organizer_name == "WCS Umeå"
        assert event.organizer_qid == "Q16"

    def test_warns_for_unknown_community(self, caplog):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/dala-westies")
        event.soup = MagicMock()
        header = MagicMock()
        header.get_text.return_value = "Dala Westies"
        event.soup.select_one.return_value = header
        event.parse_community_name()
        assert "Could not match organizer qid" in caplog.text
        assert event.organizer_name == "Dala Westies"
        assert event.organizer_qid == ""

    def test_handles_missing_header(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        event.soup = MagicMock()
        event.soup.select_one.return_value = None
        event.parse_community_name()
        assert event.organizer_name == ""
        assert event.organizer_qid == ""


class TestParseDescription:
    def test_parses_description(self):
        card_soup = MagicMock()
        desc_elem = MagicMock()
        desc_elem.get_text.return_value = "Test description"
        card_soup.find.return_value = desc_elem
        result = OnbeatEvents.parse_description(card_soup)
        assert result == "Test description"

    def test_returns_empty_when_no_desc(self):
        card_soup = MagicMock()
        card_soup.find.return_value = None
        result = OnbeatEvents.parse_description(card_soup)
        assert result == ""


class TestParseTimeRange:
    def test_parses_time_range_with_start_and_end(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        event.parse_time_range("20:00 - 21:15")
        assert event.start_time == "20:00"
        assert event.end_time == "21:15"

    def test_parses_single_time(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        event.parse_time_range("20:00")
        assert event.start_time == "20:00"
        assert event.end_time == ""

    def test_handles_empty_value(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        event.parse_time_range("")
        assert event.start_time == ""
        assert event.end_time == ""


class TestHasNoCoursesMessage:
    def test_returns_true_when_no_courses(self):
        card = MagicMock()
        p_elem = MagicMock()
        p_elem.get_text.return_value = "Sorry, no available courses"
        card.find.return_value = p_elem
        result = OnbeatEvents.has_no_courses_message(card)
        assert result is True

    def test_returns_true_when_sorry(self):
        card = MagicMock()
        p_elem = MagicMock()
        p_elem.get_text.return_value = "Sorry, we are full"
        card.find.return_value = p_elem
        result = OnbeatEvents.has_no_courses_message(card)
        assert result is True

    def test_returns_false_when_courses_exist(self):
        card = MagicMock()
        card.find.return_value = None
        result = OnbeatEvents.has_no_courses_message(card)
        assert result is False


class TestFindCards:
    def test_raises_when_no_container(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        event.soup = MagicMock()
        event.soup.find.return_value = None
        with pytest.raises(Exception, match="No container found"):
            event.find_cards()

    def test_finds_cards(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        event.soup = MagicMock()
        container = MagicMock()
        container.find_all.return_value = [MagicMock(), MagicMock()]
        event.soup.find.return_value = container
        event.find_cards()
        assert len(event.cards) == 2


class TestFetchPage:
    @patch("requests.get")
    def test_fetch_page(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = "<html><body>Test</body></html>"
        mock_get.return_value = mock_response
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        event.fetch_page()
        assert event.soup is not None
        mock_get.assert_called_once_with("https://onbeat.dance/club/test")


class TestParseCardUrl:
    def test_parses_url(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        card = MagicMock()
        a_elem = MagicMock()
        a_elem.__getitem__.return_value = "/club/test-event"
        card.find.return_value = a_elem
        url, event_id = event.parse_card_url(card)
        assert url == "https://onbeat.dance/club/test-event"
        assert event_id == "club/test-event"

    def test_returns_empty_for_no_card(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        url, event_id = event.parse_card_url(None)
        assert url == ""
        assert event_id == ""

    def test_returns_empty_for_no_anchor(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        card = MagicMock()
        card.find.return_value = None
        url, event_id = event.parse_card_url(card)
        assert url == ""
        assert event_id == ""


class TestCommunityQidMap:
    def test_inactive_community_returns_inactive(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        assert event.map_community_qid("West Coast Nights") == "inactive"

    def test_inactive_community_z_dance(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        assert event.map_community_qid("Z Dance Experience") == "inactive"


class TestParseDatetime:
    def test_parses_datetime_with_time(self):
        result = OnbeatEvents.parse_datetime("2025-04-15", "18:00")
        assert result is not None
        assert result.year == 2025
        assert result.month == 4
        assert result.day == 15
        assert result.hour == 18
        assert result.minute == 0

    def test_parses_datetime_without_time(self):
        result = OnbeatEvents.parse_datetime("2025-04-15", None)
        assert result is not None
        assert result.year == 2025
        assert result.month == 4
        assert result.day == 15

    def test_returns_none_for_empty_date(self):
        result = OnbeatEvents.parse_datetime("", "18:00")
        assert result is None

    def test_returns_none_for_invalid_format(self):
        result = OnbeatEvents.parse_datetime("invalid", "18:00")
        assert result is None


class TestParseDatetimeRange:
    def test_parses_range_with_start_and_end(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        event.parse_datetime_range("2025-04-15", "18:00 - 20:00")
        assert event.start_date is not None
        assert event.end_date is not None
        assert event.start_date.hour == 18
        assert event.end_date.hour == 20

    def test_parses_single_time(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        event.parse_datetime_range("2025-04-15", "18:00")
        assert event.start_date is not None
        assert event.end_date is None
        assert event.start_date.hour == 18

    def test_parses_date_only(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        event.parse_datetime_range("2025-04-15", None)
        assert event.start_date is not None
        assert event.start_date.hour == 0

    def test_handles_empty_date(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        event.parse_datetime_range("", "18:00")
        assert event.start_date is None

    def test_handles_invalid_format(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        event.parse_datetime_range("invalid", "18:00")
        assert event.start_date is None


class TestParseCommunityNameFetchesPage:
    @patch("requests.get")
    def test_fetches_page_when_soup_is_none(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = "<html><body><div class='row mt-3'><h5><b>Test Club</b></h5></div></body></html>"
        mock_get.return_value = mock_response
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        event.soup = None
        event.parse_community_name()
        assert event.organizer_name == "Test Club"
        assert event.organizer_qid == ""


class TestFindCardsFetchesPage:
    @patch("requests.get")
    def test_fetches_page_when_soup_is_none(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = "<html><body><div id='clubCollapse-1'><div class='card custom-card'></div></div></body></html>"
        mock_get.return_value = mock_response
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        event.soup = None
        event.find_cards()
        assert len(event.cards) == 1


class TestHasNoCoursesMessageEdge:
    def test_returns_false_when_msg_elem_is_none(self):
        card = MagicMock()
        card.find.return_value = None
        result = OnbeatEvents.has_no_courses_message(card)
        assert result is False


class TestParseTimeRangeEdgeCases:
    def test_logs_warning_on_split_error(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        bad_value = MagicMock()
        bad_value.strip.side_effect = AttributeError("mock error")
        with patch("src.models.onbeat.events.logger") as mock_logger:
            event.parse_time_range(bad_value)
            mock_logger.warning.assert_called()


class TestPriceOverrideMap:
    def test_rockthebarn_price_override_exists(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        assert "rockthebarn" in event.price_override_map
        assert event.price_override_map["rockthebarn"] == 1800

    def test_price_override_map_is_populated(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        assert len(event.price_override_map) >= 1


class TestMapVenueQidCaseInsensitive:
    def test_venue_qid_map_values_are_strings(self):
        event = OnbeatEvents(page_url="https://onbeat.dance/club/test")
        for key, qid in event.venue_qid_map.items():
            assert isinstance(key, str), f"Key {key} is not a string"
            assert isinstance(qid, str), f"QID {qid} is not a string"
