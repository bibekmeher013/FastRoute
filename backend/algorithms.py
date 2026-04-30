"""
algorithms.py — Custom route-optimisation implementations
=========================================================
Each solver returns a dict:
  {
    "route"    : [[lat, lng], ...],
    "distance" : float (km),
    "time_ms"  : float,
    "algorithm": str,
    "iterations": int   (where applicable)
  }

Algorithms implemented
----------------------
1. Nearest Neighbour Heuristic  — O(n²)  greedy, fast
2. 2-Opt Local Search           — O(n²) per pass, improves any initial tour
3. OR-Tools (metaheuristic)     — near-optimal, slower
4. Greedy Edge Insertion        — build tour by adding shortest non-conflicting edges
"""

import time
import math
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from utils import create_distance_matrix, haversine


# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────

def _tour_distance_m(tour_indices, matrix):
    """Total tour distance in metres given index list (must close: last→first)."""
    return sum(matrix[tour_indices[i]][tour_indices[i + 1]]
               for i in range(len(tour_indices) - 1))


def _indices_to_coords(indices, points):
    return [points[i] for i in indices]


def _m_to_km(metres):
    return round(metres / 1000, 3)


# ──────────────────────────────────────────────
#  1. Nearest Neighbour Heuristic
# ──────────────────────────────────────────────

def nearest_neighbour(points):
    """
    Nearest Neighbour greedy heuristic.
    Time complexity: O(n²)
    Quality: typically 20-25% above optimal (worst-case unbounded)
    """
    t0 = time.perf_counter()
    matrix = create_distance_matrix(points)
    n = len(points)

    unvisited = set(range(1, n))
    tour = [0]

    while unvisited:
        current = tour[-1]
        nearest = min(unvisited, key=lambda j: matrix[current][j])
        tour.append(nearest)
        unvisited.remove(nearest)

    tour.append(0)   # return to start
    dist = _tour_distance_m(tour, matrix)
    elapsed = (time.perf_counter() - t0) * 1000

    return {
        "route": _indices_to_coords(tour, points),
        "distance": _m_to_km(dist),
        "time_ms": round(elapsed, 2),
        "algorithm": "Nearest Neighbour",
        "iterations": n - 1,
    }


# ──────────────────────────────────────────────
#  2. 2-Opt Local Search
# ──────────────────────────────────────────────

def two_opt(points, max_iterations=500):
    """
    2-Opt local search improvement over a Nearest Neighbour seed tour.
    Reverses segments of the tour to eliminate crossing edges.
    Time complexity: O(n²) per iteration
    """
    t0 = time.perf_counter()
    matrix = create_distance_matrix(points)
    n = len(points)

    # seed with nearest neighbour (without timing overhead)
    unvisited = set(range(1, n))
    tour = [0]
    while unvisited:
        c = tour[-1]
        nb = min(unvisited, key=lambda j: matrix[c][j])
        tour.append(nb)
        unvisited.remove(nb)
    tour.append(0)

    improved = True
    iters = 0
    best_dist = _tour_distance_m(tour, matrix)

    while improved and iters < max_iterations:
        improved = False
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                # cost of reversing segment [i..j]
                delta = (
                    matrix[tour[i - 1]][tour[j]]
                    + matrix[tour[i]][tour[j + 1]]
                    - matrix[tour[i - 1]][tour[i]]
                    - matrix[tour[j]][tour[j + 1]]
                )
                if delta < -1:          # improvement found
                    tour[i:j + 1] = tour[i:j + 1][::-1]
                    best_dist += delta
                    improved = True
        iters += 1

    elapsed = (time.perf_counter() - t0) * 1000
    return {
        "route": _indices_to_coords(tour, points),
        "distance": _m_to_km(best_dist),
        "time_ms": round(elapsed, 2),
        "algorithm": "2-Opt Local Search",
        "iterations": iters,
    }


# ──────────────────────────────────────────────
#  3. Greedy Edge Insertion
# ──────────────────────────────────────────────

def greedy_edge(points):
    """
    Greedy edge-insertion heuristic.
    Sort all edges by distance, add each if it doesn't create a degree-3 node
    or a premature cycle.  Forms a Hamiltonian path, then closes it.
    Time complexity: O(n² log n)
    """
    t0 = time.perf_counter()
    matrix = create_distance_matrix(points)
    n = len(points)

    # generate and sort all edges
    edges = sorted(
        ((matrix[i][j], i, j) for i in range(n) for j in range(i + 1, n)),
        key=lambda e: e[0],
    )

    degree = [0] * n
    adj = [[] for _ in range(n)]   # adjacency list

    # union-find for cycle detection
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        parent[find(x)] = find(y)

    edge_count = 0
    for dist, u, v in edges:
        if edge_count == n - 1:
            break
        # skip if either node already has degree 2
        if degree[u] >= 2 or degree[v] >= 2:
            continue
        # skip if adding creates a cycle (unless it's the last edge)
        if find(u) == find(v):
            continue
        adj[u].append(v)
        adj[v].append(u)
        degree[u] += 1
        degree[v] += 1
        union(u, v)
        edge_count += 1

    # build tour from adjacency list (start at degree-1 node)
    starts = [i for i in range(n) if degree[i] == 1]
    start = starts[0] if starts else 0
    visited = [False] * n
    tour = [start]
    visited[start] = True

    for _ in range(n - 1):
        curr = tour[-1]
        moved = False
        for nb in adj[curr]:
            if not visited[nb]:
                tour.append(nb)
                visited[nb] = True
                moved = True
                break
        if not moved:
            # fallback: pick nearest unvisited
            remaining = [i for i in range(n) if not visited[i]]
            if remaining:
                nb = min(remaining, key=lambda j: matrix[curr][j])
                tour.append(nb)
                visited[nb] = True

    tour.append(tour[0])   # close tour
    dist_total = _tour_distance_m(tour, matrix)
    elapsed = (time.perf_counter() - t0) * 1000

    return {
        "route": _indices_to_coords(tour, points),
        "distance": _m_to_km(dist_total),
        "time_ms": round(elapsed, 2),
        "algorithm": "Greedy Edge Insertion",
        "iterations": edge_count,
    }


# ──────────────────────────────────────────────
#  4. OR-Tools Metaheuristic (Guided Local Search)
# ──────────────────────────────────────────────

def ortools_tsp(points, time_limit=10):
    """
    OR-Tools with Guided Local Search metaheuristic.
    Best solution quality; higher computation time.
    """
    t0 = time.perf_counter()
    matrix = create_distance_matrix(points)
    n = len(points)

    manager = pywrapcp.RoutingIndexManager(n, 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def dist_cb(fi, ti):
        return matrix[manager.IndexToNode(fi)][manager.IndexToNode(ti)]

    cb = routing.RegisterTransitCallback(dist_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(cb)

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds = time_limit

    sol = routing.SolveWithParameters(params)
    elapsed = (time.perf_counter() - t0) * 1000

    if not sol:
        return {"route": [], "distance": 0, "time_ms": round(elapsed, 2),
                "algorithm": "OR-Tools GLS", "iterations": 0}

    tour, idx = [], routing.Start(0)
    while not routing.IsEnd(idx):
        tour.append(manager.IndexToNode(idx))
        idx = sol.Value(routing.NextVar(idx))
    tour.append(tour[0])

    dist = _tour_distance_m(tour, matrix)
    return {
        "route": _indices_to_coords(tour, points),
        "distance": _m_to_km(dist),
        "time_ms": round(elapsed, 2),
        "algorithm": "OR-Tools (GLS)",
        "iterations": time_limit,
    }


# ──────────────────────────────────────────────
#  Compare — run all 4 on same input
# ──────────────────────────────────────────────

def compare_all(points):
    """Run all four algorithms on the same point set and return ranked results."""
    results = [
        nearest_neighbour(points),
        two_opt(points),
        greedy_edge(points),
        ortools_tsp(points, time_limit=5),
    ]
    # rank by distance
    valid = [r for r in results if r["distance"] > 0]
    valid.sort(key=lambda r: r["distance"])
    best = valid[0]["distance"] if valid else 1
    for r in valid:
        r["gap_pct"] = round((r["distance"] - best) / best * 100, 1)
        r["rank"] = valid.index(r) + 1
    return valid
