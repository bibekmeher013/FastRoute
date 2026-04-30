"""
FastRoute API v2.0
==================
Endpoints:
  POST /path              — shortest path
  POST /tsp               — OR-Tools TSP
  POST /cvrp              — Capacitated VRP
  POST /compare           — run all 4 TSP algorithms and compare
  GET  /benchmarks        — list classic benchmark problems
  GET  /benchmarks/{name} — load a benchmark instance
  GET  /health            — server health check
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional

from routing    import solve_path, solve_tsp, solve_cvrp, stitch_route
from algorithms import compare_all
from benchmarks import get_benchmark, list_benchmarks

app = FastAPI(title="FastRoute API", version="2.0",
              description="Multi-algorithm route optimisation — university project")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)


# ── Models ────────────────────────────────────────────────────────────────────

class PathRequest(BaseModel):
    points: List[List[float]]

class TspRequest(BaseModel):
    points: List[List[float]]
    use_roads: bool = False

class CvrpRequest(BaseModel):
    depot: List[float]
    customers: List[List[float]]
    demands: List[int]
    capacities: List[int]
    use_roads: bool = False

class CompareRequest(BaseModel):
    points: List[List[float]]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0"}


@app.post("/path")
def path(req: PathRequest):
    if len(req.points) < 2:
        raise HTTPException(400, "Need at least 2 points")
    return solve_path(req.points[0], req.points[1])


@app.post("/tsp")
def tsp(req: TspRequest):
    if len(req.points) < 3:
        raise HTTPException(400, "TSP requires at least 3 points")
    return solve_tsp(req.points, use_roads=req.use_roads)


@app.post("/cvrp")
def cvrp(req: CvrpRequest):
    if not req.customers:
        raise HTTPException(400, "Add at least one customer")
    if not req.capacities:
        raise HTTPException(400, "Add at least one vehicle")
    if len(req.demands) != len(req.customers):
        raise HTTPException(400, "demands length must match customers length")
    return solve_cvrp(
        req.depot, req.customers, req.demands, req.capacities,
        use_roads=req.use_roads
    )


@app.post("/compare")
def compare(req: CompareRequest):
    """
    Run Nearest Neighbour, 2-Opt, Greedy Edge, and OR-Tools GLS
    on the same point set and return ranked results WITH actual road geometry.
    """
    if len(req.points) < 4:
        raise HTTPException(400, "Comparison needs at least 4 points")
    results = compare_all(req.points)

    # Stitch real road geometry for every algorithm route
    for r in results:
        if r.get("route"):
            r["road_route"] = stitch_route(r["route"])
        else:
            r["road_route"] = []

    return {"results": results, "point_count": len(req.points)}


@app.get("/benchmarks")
def benchmarks():
    return {"benchmarks": list_benchmarks()}


@app.get("/benchmarks/{name}")
def benchmark(name: str):
    b = get_benchmark(name)
    if not b:
        raise HTTPException(404, f"Benchmark '{name}' not found")
    return b
