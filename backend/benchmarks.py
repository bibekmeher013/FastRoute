"""
benchmarks.py — Classic TSP benchmark instances
================================================
Provides pre-loaded named problems so users can test and compare
algorithms without manually placing points.

Sources:
- berlin52 : 52 cities in Berlin (Groetschel 1977), optimal = 7542 units
- burma14  : 14 cities in Burma (Zaw Win), optimal = 3323 units
- Custom small/medium test cases
"""

# berlin52 — coordinates (x, y) scaled to lat/lng around Berlin
# Original Euclidean coords mapped into ~Berlin bounding box
_BERLIN_LAT_BASE, _BERLIN_LNG_BASE = 52.45, 13.25
_SCALE = 0.006

BERLIN52_RAW = [
    (565,575),(25,185),(345,750),(945,685),(845,655),(880,660),(25,230),
    (525,1000),(580,1175),(650,1130),(1605,620),(1220,580),(1465,200),
    (1530,5),(845,680),(725,370),(145,665),(415,635),(510,875),(560,365),
    (300,465),(520,585),(480,415),(835,625),(975,580),(1215,245),(1320,315),
    (1250,400),(660,180),(410,250),(420,555),(575,665),(1150,1160),(700,580),
    (685,595),(685,610),(770,610),(795,645),(720,635),(760,650),(475,960),
    (95,260),(875,920),(700,500),(555,815),(830,485),(1170,65),(830,610),
    (605,625),(595,360),(1340,725),(1740,245),
]

def berlin52():
    return {
        "name": "Berlin 52",
        "description": "52 cities in Berlin — classic benchmark. Known optimal: 7542 units.",
        "optimal_known": 7542,
        "points": [
            [_BERLIN_LAT_BASE + (y / 1000) * _SCALE * 100,
             _BERLIN_LNG_BASE + (x / 1000) * _SCALE * 100]
            for x, y in BERLIN52_RAW
        ]
    }

def burma14():
    """14-city Burma problem — small, optimal solution known exactly."""
    raw = [
        (16.47, 96.10),(16.47, 94.44),(20.09, 92.54),(22.39, 93.37),
        (25.23, 97.24),(22.00, 96.05),(20.47, 97.02),(17.20, 96.29),
        (16.30, 97.38),(14.05, 98.12),(16.53, 97.38),(21.52, 95.59),
        (19.41, 97.13),(20.09, 94.55),
    ]
    return {
        "name": "Burma 14",
        "description": "14 cities in Burma — small instance. Known optimal: 3323 units.",
        "optimal_known": 3323,
        "points": [[lat, lng] for lat, lng in raw]
    }

def random_20():
    """20-point synthetic cluster test case around Bangalore."""
    import math
    pts = []
    centers = [(12.97, 77.59), (12.95, 77.65), (13.02, 77.55)]
    import random; random.seed(42)
    for cx, cy in centers:
        for _ in range(6):
            pts.append([cx + random.uniform(-0.05, 0.05),
                        cy + random.uniform(-0.05, 0.05)])
    pts = pts[:20]
    return {
        "name": "Synthetic 20",
        "description": "20 synthetic clustered points around Bangalore.",
        "optimal_known": None,
        "points": pts
    }

BENCHMARKS = {
    "berlin52": berlin52,
    "burma14":  burma14,
    "random20": random_20,
}

def get_benchmark(name):
    fn = BENCHMARKS.get(name)
    return fn() if fn else None

def list_benchmarks():
    return [{"id": k, **fn()} for k, fn in BENCHMARKS.items()]
