from pydantic import ConfigDict

from src.models.base import DanceBaseModel


class FuzzyMatchResult(DanceBaseModel):
    """Result from fuzzy matching."""
    original_input: str
    matched_label: str
    qid: str
    score: float
    cleaned_input: str
    cleaned_label: str
    false_friend: bool = False
    
    model_config = ConfigDict(extra="forbid", frozen=True)


class FuzzyMatchResultQid(DanceBaseModel):
    """Result from fuzzy matching with QID return."""
    matched_label: str
    qid: str
    score: float
    cleaned_input: str
    false_friend: bool = False
    
    model_config = ConfigDict(extra="forbid", frozen=True)