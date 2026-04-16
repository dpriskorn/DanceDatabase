import pytest

from src.utils.fuzzy import remove_terms, normalize_for_fuzzy


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