from pydantic import BaseModel


class FuzzyMatchResult(BaseModel):
    """Result from fuzzy matching."""
    original_input: str
    matched_label: str
    qid: str
    score: float
    cleaned_input: str
    cleaned_label: str
    false_friend: bool = False
    
    model_config = {"frozen": True}


class FuzzyMatchResultQid(BaseModel):
    """Result from fuzzy matching with QID return."""
    matched_label: str
    qid: str
    score: float
    cleaned_input: str
    false_friend: bool = False
    
    model_config = {"frozen": True}