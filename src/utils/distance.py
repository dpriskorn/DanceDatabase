import math


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two points in km using Haversine formula."""
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def coordinate_bounding_box(lat: float, lng: float, threshold_km: float) -> tuple[float, float, float, float]:
    """Calculate bounding box for coordinate search.

    Returns (lng_min, lng_max, lat_min, lat_max).
    """
    lat_delta = threshold_km / 111
    lng_delta = threshold_km / (111 * math.cos(math.radians(lat)))
    return lng - lng_delta, lng + lng_delta, lat - lat_delta, lat + lat_delta