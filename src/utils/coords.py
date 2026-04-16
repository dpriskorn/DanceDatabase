import json
from typing import Any


def parse_coords(input_str: str) -> dict[str, float] | None:
    """Parse coordinate input in various formats.
    
    Supports:
    - Simple: "59.355601,18.0993459"
    - Dict: '{"lat": 59.355601, "lng": 18.0993459}'
    - With whitespace: "59.355601,\n    \"lng\": 18.0993459,"
    
    Returns:
        dict with 'lat' and 'lng' keys, or None if invalid.
    """
    if not input_str:
        return None
    
    cleaned = input_str.replace(" ", "").replace("\n", "").replace("\t", "")
    
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict) and "lat" in data and "lng" in data:
            return {"lat": float(data["lat"]), "lng": float(data["lng"])}
    except json.JSONDecodeError:
        pass
    
    try:
        parts = cleaned.split(",")
        if len(parts) == 2:
            lat = float(parts[0])
            lng = float(parts[1])
            return {"lat": lat, "lng": lng}
    except ValueError:
        pass
    
    return None