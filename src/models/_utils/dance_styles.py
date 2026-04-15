DANCE_STYLE_MAP = {
    "fox": "Q23",
    "west coast swing": "Q15",
    "modern fox": "Q23",
    "bugg": "Q485",
    "casanovas": "Q4",
    "socialdans": "Q4",
}

STYLE_KEYS_TO_QIDS = {style: qid for style, qid in DANCE_STYLE_MAP.items()}


def get_style_qid(text: str) -> set[str]:
    """Return all matching dance style QIDs for a given text (case-insensitive)."""
    qids = set()
    text_lower = text.lower()
    for style, qid in DANCE_STYLE_MAP.items():
        if style in text_lower:
            qids.add(qid)
    return qids
