"""
Unit tests for FastRoute algorithms
Run with: python -m pytest tests/ -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from utils import haversine, create_distance_matrix
from algorithms import nearest_neighbour, two_opt, greedy_edge, ortools_tsp, compare_all

# ── Fixtures ──────────────────────────────────────────────────────────────────

SQUARE = [[0.0, 0.0],[0.0, 1.0],[1.0, 1.0],[1.0, 0.0]]          # 4-point square
BURMA  = [[16.47,96.10],[16.47,94.44],[20.09,92.54],[22.39,93.37],
          [25.23,97.24],[22.00,96.05],[20.47,97.02],[17.20,96.29]]  # 8-pt subset


# ── Utils tests ───────────────────────────────────────────────────────────────

def test_haversine_same_point():
    assert haversine([10.0, 20.0], [10.0, 20.0]) == 0

def test_haversine_known():
    # London to Paris ≈ 340 km
    d = haversine([51.5074, -0.1278], [48.8566, 2.3522])
    assert 330_000 < d < 350_000, f"Expected ~340 000 m, got {d}"

def test_distance_matrix_shape():
    m = create_distance_matrix(SQUARE)
    assert len(m) == 4 and all(len(row) == 4 for row in m)

def test_distance_matrix_symmetric():
    m = create_distance_matrix(SQUARE)
    for i in range(4):
        for j in range(4):
            assert m[i][j] == m[j][i]

def test_distance_matrix_diagonal_zero():
    m = create_distance_matrix(SQUARE)
    assert all(m[i][i] == 0 for i in range(4))


# ── Algorithm output structure tests ─────────────────────────────────────────

REQUIRED_KEYS = {"route", "distance", "time_ms", "algorithm", "iterations"}

@pytest.mark.parametrize("fn", [nearest_neighbour, two_opt, greedy_edge])
def test_algorithm_keys(fn):
    res = fn(SQUARE)
    assert REQUIRED_KEYS.issubset(res.keys()), f"Missing keys in {fn.__name__}"

@pytest.mark.parametrize("fn", [nearest_neighbour, two_opt, greedy_edge])
def test_algorithm_tour_closes(fn):
    res = fn(SQUARE)
    assert res["route"][0] == res["route"][-1], "Tour must return to start"

@pytest.mark.parametrize("fn", [nearest_neighbour, two_opt, greedy_edge])
def test_algorithm_visits_all(fn):
    res = fn(SQUARE)
    interior = res["route"][:-1]          # exclude closing duplicate
    assert len(interior) == len(SQUARE), "Must visit all points"

@pytest.mark.parametrize("fn", [nearest_neighbour, two_opt, greedy_edge])
def test_algorithm_positive_distance(fn):
    res = fn(SQUARE)
    assert res["distance"] > 0

@pytest.mark.parametrize("fn", [nearest_neighbour, two_opt, greedy_edge])
def test_algorithm_time_recorded(fn):
    res = fn(SQUARE)
    assert res["time_ms"] >= 0


# ── Quality tests ─────────────────────────────────────────────────────────────

def test_2opt_not_worse_than_nn():
    """2-Opt should produce a tour at least as good as Nearest Neighbour."""
    nn  = nearest_neighbour(BURMA)["distance"]
    opt = two_opt(BURMA)["distance"]
    assert opt <= nn * 1.01, f"2-Opt ({opt}) worse than NN ({nn})"

def test_ortools_not_worse_than_nn():
    nn  = nearest_neighbour(BURMA)["distance"]
    ort = ortools_tsp(BURMA, time_limit=3)["distance"]
    assert ort <= nn * 1.01, f"OR-Tools ({ort}) worse than NN ({nn})"


# ── Compare tests ─────────────────────────────────────────────────────────────

def test_compare_returns_4_results():
    res = compare_all(BURMA)
    assert len(res) == 4

def test_compare_sorted_by_distance():
    res = compare_all(BURMA)
    dists = [r["distance"] for r in res]
    assert dists == sorted(dists)

def test_compare_rank1_gap_zero():
    res = compare_all(BURMA)
    assert res[0]["gap_pct"] == 0.0

def test_compare_has_gap_field():
    res = compare_all(BURMA)
    assert all("gap_pct" in r for r in res)
