import pytest

from src.utils.fuzzy import is_false_fuzzy_match, normalize_for_fuzzy, remove_terms
from src.utils.fuzzy_models import FuzzyMatchResult, FuzzyMatchResultQid


class TestRemoveTerms:
    def test_removes_single_term(self):
        result = remove_terms("Folkets Hus Gård", ["folkets hus", "förening", "gård"])
        assert result == ""

    def test_removes_multiple_terms(self):
        result = remove_terms("Test förening gård", ["förening", "gård"])
        assert result == "Test"

    def test_case_insensitive(self):
        result = remove_terms("FOLKETS HUS", ["folkets hus"])
        assert result == ""

    def test_preserves_text_without_terms(self):
        result = remove_terms("Test Venue", ["folkets hus"])
        assert result == "Test Venue"

    def test_empty_text(self):
        result = remove_terms("", ["term"])
        assert result == ""

    def test_empty_terms(self):
        result = remove_terms("Test", [])
        assert result == "Test"


class TestNormalizeForFuzzy:
    def test_lowercase_and_strip(self):
        result = normalize_for_fuzzy("  Test Venue  ")
        assert result == "test venue"

    def test_remove_terms(self):
        result = normalize_for_fuzzy("Test förening gård", ["förening", "gård"])
        assert result == "test"

    def test_empty(self):
        result = normalize_for_fuzzy("", ["term"])
        assert result == ""

    def test_no_terms(self):
        result = normalize_for_fuzzy("Test", None)
        assert result == "test"


class TestIsFalseFriend:
    def test_known_false_friend(self):
        result = is_false_fuzzy_match("alvesta", "avesta")
        assert result is True

    def test_not_false_friend(self):
        result = is_false_fuzzy_match("stockholm", "göteborg")
        assert result is False

    def test_symmetric(self):
        assert is_false_fuzzy_match("alvesta", "avesta") is True
        assert is_false_fuzzy_match("avesta", "alvesta") is True


class TestFuzzyMatchResultModels:
    def test_fuzzy_match_result_qid_creation(self):
        result = FuzzyMatchResultQid(
            matched_label="Test Venue",
            qid="Q123",
            score=90.5,
            cleaned_input="test venue",
            false_friend=False,
        )
        assert result.matched_label == "Test Venue"
        assert result.qid == "Q123"
        assert result.score == 90.5
        assert result.false_friend is False

    def test_fuzzy_match_result_creation(self):
        result = FuzzyMatchResult(
            original_input="Original",
            matched_label="Matched",
            qid="Q456",
            score=85.0,
            cleaned_input="orig",
            cleaned_label="match",
            false_friend=True,
        )
        assert result.original_input == "Original"
        assert result.false_friend is True
        assert result.qid == "Q456"