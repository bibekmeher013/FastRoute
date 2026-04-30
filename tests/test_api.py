"""
Integration tests for FastRoute API endpoints.
Requires the backend to be running: uvicorn app:app
Run with: python -m pytest tests/test_api.py -v
Or mock-test without running server using TestClient.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

# ── Health ────────────────────────────────────────────────────────────────────

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

# ── Path ──────────────────────────────────────────────────────────────────────

def test_path_basic():
    r = client.post("/path", json={"points": [[12.9, 77.5], [13.0, 77.6]]})
    assert r.status_code == 200
    data = r.json()
    assert "route" in data
    assert len(data["route"]) == 2

def test_path_too_few_points():
    r = client.post("/path", json={"points": [[12.9, 77.5]]})
    assert r.status_code == 400

# ── TSP ───────────────────────────────────────────────────────────────────────

SQUARE = [[0.0,0.0],[0.0,1.0],[1.0,1.0],[1.0,0.0],[0.5,0.5]]

def test_tsp_basic():
    r = client.post("/tsp", json={"points": SQUARE})
    assert r.status_code == 200
    data = r.json()
    assert "route" in data
    assert len(data["route"]) >= len(SQUARE)   # includes return leg

def test_tsp_too_few_points():
    r = client.post("/tsp", json={"points": [[0,0],[1,1]]})
    assert r.status_code == 400

def test_tsp_returns_distance():
    r = client.post("/tsp", json={"points": SQUARE})
    assert r.status_code == 200
    assert "distance" in r.json()

# ── CVRP ──────────────────────────────────────────────────────────────────────

DEPOT = [0.0, 0.0]
CUSTOMERS = [[0.1,0.1],[0.2,0.2],[0.3,0.1],[0.1,0.3]]
DEMANDS   = [10, 20, 15, 25]
CAPS      = [60, 60]

def test_cvrp_basic():
    r = client.post("/cvrp", json={
        "depot": DEPOT, "customers": CUSTOMERS,
        "demands": DEMANDS, "capacities": CAPS
    })
    assert r.status_code == 200
    data = r.json()
    assert "routes" in data
    assert "vehicles_used" in data

def test_cvrp_many_vehicles():
    """Should work fine with 6+ vehicles."""
    caps = [30, 30, 30, 30, 30, 30]
    r = client.post("/cvrp", json={
        "depot": DEPOT, "customers": CUSTOMERS,
        "demands": DEMANDS, "capacities": caps
    })
    assert r.status_code == 200

def test_cvrp_demand_mismatch():
    r = client.post("/cvrp", json={
        "depot": DEPOT, "customers": CUSTOMERS,
        "demands": [10, 20],   # wrong length
        "capacities": CAPS
    })
    assert r.status_code == 400

def test_cvrp_no_customers():
    r = client.post("/cvrp", json={
        "depot": DEPOT, "customers": [],
        "demands": [], "capacities": CAPS
    })
    assert r.status_code == 400

# ── Compare ───────────────────────────────────────────────────────────────────

COMPARE_PTS = [[0.0,0.0],[0.0,1.0],[1.0,1.0],[1.0,0.0],[0.5,0.8],[0.8,0.3]]

def test_compare_basic():
    r = client.post("/compare", json={"points": COMPARE_PTS})
    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    assert len(data["results"]) == 4

def test_compare_sorted():
    r = client.post("/compare", json={"points": COMPARE_PTS})
    dists = [x["distance"] for x in r.json()["results"]]
    assert dists == sorted(dists)

def test_compare_has_all_algorithms():
    r = client.post("/compare", json={"points": COMPARE_PTS})
    algos = {x["algorithm"] for x in r.json()["results"]}
    expected = {"Nearest Neighbour","2-Opt Local Search","Greedy Edge Insertion","OR-Tools (GLS)"}
    assert expected == algos

def test_compare_too_few_points():
    r = client.post("/compare", json={"points": [[0,0],[1,1],[0,1]]})
    assert r.status_code == 400

# ── Benchmarks ────────────────────────────────────────────────────────────────

def test_benchmarks_list():
    r = client.get("/benchmarks")
    assert r.status_code == 200
    data = r.json()
    assert "benchmarks" in data
    assert len(data["benchmarks"]) >= 3

def test_benchmark_burma14():
    r = client.get("/benchmarks/burma14")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Burma 14"
    assert len(data["points"]) == 14

def test_benchmark_berlin52():
    r = client.get("/benchmarks/berlin52")
    assert r.status_code == 200
    assert len(r.json()["points"]) == 52

def test_benchmark_not_found():
    r = client.get("/benchmarks/doesnotexist")
    assert r.status_code == 404
