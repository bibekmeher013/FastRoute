"""
utils.py — Distance matrix construction
Supports Haversine (default) and OSRM real-road distances.
"""
import math
import urllib.request
import json


def haversine(p1, p2):
    """Great-circle distance in metres between two [lat, lng] points."""
    R = 6_371_000
    lat1, lng1 = math.radians(p1[0]), math.radians(p1[1])
    lat2, lng2 = math.radians(p2[0]), math.radians(p2[1])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return int(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def create_distance_matrix(points):
    """Build an n×n Haversine distance matrix (metres, integer)."""
    n = len(points)
    return [[haversine(points[i], points[j]) for j in range(n)] for i in range(n)]


def create_osrm_matrix(points, timeout=8):
    """
    Build an n×n matrix using OSRM road distances (metres, integer).
    Falls back to Haversine if OSRM is unavailable.
    """
    coords = ";".join(f"{p[1]},{p[0]}" for p in points)   # OSRM wants lng,lat
    url = f"https://router.project-osrm.org/table/v1/driving/{coords}?annotations=distance"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FastRoute/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        if data.get("code") == "Ok":
            return [[int(v) for v in row] for row in data["distances"]]
    except Exception:
        pass
    # fallback
    return create_distance_matrix(points)
