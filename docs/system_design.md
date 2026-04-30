# FastRoute — System Design Document

## 1. Overview

FastRoute is a web-based route optimisation platform that implements and compares multiple
vehicle routing algorithms. The system is designed as a client-server application with a
Python backend (FastAPI) and a browser-based frontend (Leaflet.js).

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (Browser)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  map.js      │  │  style.css   │  │  index.html   │  │
│  │  Leaflet.js  │  │  Dark/Light  │  │  4-mode UI    │  │
│  └──────┬───────┘  └──────────────┘  └───────────────┘  │
│         │  HTTP POST (JSON)                              │
└─────────┼───────────────────────────────────────────────┘
          │
          ▼  localhost:8000
┌─────────────────────────────────────────────────────────┐
│                  BACKEND (FastAPI)                       │
│                                                         │
│  ┌──────────┐  ┌────────────┐  ┌──────────────────────┐ │
│  │  app.py  │  │algorithms  │  │  routing.py (CVRP/   │ │
│  │  Routes  │  │  .py       │  │  TSP via OR-Tools)   │ │
│  └──────────┘  └────────────┘  └──────────────────────┘ │
│                                                         │
│  ┌────────────┐  ┌──────────────────────────────────┐   │
│  │benchmarks  │  │  utils.py                        │   │
│  │  .py       │  │  Haversine / OSRM matrix         │   │
│  └────────────┘  └──────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
          │
          ▼  (optional)
┌───────────────────────┐
│  OSRM Router API      │
│  (road distances)     │
│  router.project-osrm  │
└───────────────────────┘
```

---

## 3. Algorithm Analysis

### 3.1 Nearest Neighbour (NN) Heuristic

**Category:** Constructive greedy heuristic  
**Time Complexity:** O(n²)  
**Space Complexity:** O(n)

**Description:**  
Starting from the depot, at each step visit the nearest unvisited node.
Simple and fast but tends to make poor long-distance decisions early on.

**Worst-case gap:** Unbounded (O(log n) in practice)  
**Typical gap from optimal:** 20–25%

```
NN(points):
  visited = {0}
  tour = [0]
  while visited ≠ all nodes:
    next = argmin d(current, j) for j ∉ visited
    tour.append(next)
    visited.add(next)
  tour.append(0)
  return tour
```

---

### 3.2 2-Opt Local Search

**Category:** Improvement heuristic  
**Time Complexity:** O(n²) per iteration, O(n² × k) total  
**Space Complexity:** O(n)

**Description:**  
Starts from a NN tour. Iteratively reverses segments [i..j] when doing so
reduces total tour length. Eliminates crossing edges.

**Typical gap from optimal:** 5–10%  
**Guaranteed improvement over:** Nearest Neighbour seed

```
2Opt(tour):
  repeat until no improvement:
    for i in 1..n-1:
      for j in i+1..n:
        delta = d[i-1][j] + d[i][j+1] - d[i-1][i] - d[j][j+1]
        if delta < 0:
          reverse tour[i..j]
  return tour
```

---

### 3.3 Greedy Edge Insertion

**Category:** Constructive heuristic  
**Time Complexity:** O(n² log n) (dominated by edge sort)  
**Space Complexity:** O(n²)

**Description:**  
Sort all n(n-1)/2 edges by distance. Add each edge to the solution if:
1. Neither endpoint already has degree 2
2. Adding it does not form a cycle (unless it's the final closing edge)

Uses Union-Find for O(α(n)) cycle detection.

**Typical gap from optimal:** 15–20%

---

### 3.4 OR-Tools Guided Local Search (GLS)

**Category:** Metaheuristic  
**Time Complexity:** Variable (time-limited)  
**Space Complexity:** O(n²)

**Description:**  
Google OR-Tools with Guided Local Search metaheuristic.
Uses penalty functions to escape local optima.
Seeded with PATH_CHEAPEST_ARC, then iterates under a time budget.

**Typical gap from optimal:** 0–3%  
**Trade-off:** Higher computation time

---

## 4. Algorithm Comparison Summary

| Algorithm            | Time Complexity | Quality  | Speed  | Best Use Case        |
|----------------------|-----------------|----------|--------|----------------------|
| Nearest Neighbour    | O(n²)           | Poor     | ★★★★★ | Quick baseline       |
| Greedy Edge          | O(n² log n)     | Fair     | ★★★★☆ | Medium instances     |
| 2-Opt Local Search   | O(n² × iter)    | Good     | ★★★☆☆ | Improved construction|
| OR-Tools GLS         | Time-limited    | Excellent| ★★☆☆☆ | Production solutions |

---

## 5. Distance Models

### 5.1 Haversine (Default)

Great-circle distance between two lat/lng points on the Earth's surface.

```
a = sin²(Δlat/2) + cos(lat1)·cos(lat2)·sin²(Δlng/2)
d = 2R · atan2(√a, √(1-a))      R = 6,371,000 m
```

**Pros:** Instant, no external dependency  
**Cons:** Ignores roads, terrain, one-way streets

### 5.2 OSRM Road Distances (Optional)

Uses the public OSRM routing API (`/table/v1/driving`) to compute actual
road distances between all pairs of points in a single request.

**Pros:** Realistic distances  
**Cons:** Network latency (~1–3 s), rate limited

---

## 6. Data Flow

### TSP Request
```
Client sends: { points: [[lat,lng],...] }
     ↓
app.py /tsp  →  routing.solve_tsp(points)
                    ↓
              utils.create_distance_matrix(points)  [Haversine]
                    OR
              utils.create_osrm_matrix(points)      [OSRM]
                    ↓
              OR-Tools RoutingModel (GLS, 5s limit)
                    ↓
              Returns: { route, distance }
     ↓
Client renders polyline on Leaflet map
```

### Compare Request
```
Client sends: { points: [[lat,lng],...] }
     ↓
app.py /compare  →  algorithms.compare_all(points)
                         ↓
              Runs 4 solvers in sequence:
              1. nearest_neighbour
              2. two_opt
              3. greedy_edge
              4. ortools_tsp
                         ↓
              Sorts by distance, adds gap_pct, rank
     ↓
Client renders table + SVG bar charts
```

---

## 7. API Endpoints

| Method | Endpoint              | Input                                              | Output                            |
|--------|-----------------------|----------------------------------------------------|-----------------------------------|
| GET    | `/health`             | —                                                  | `{status, version}`               |
| POST   | `/path`               | `{points}`                                         | `{route}`                         |
| POST   | `/tsp`                | `{points, use_roads}`                              | `{route, distance}`               |
| POST   | `/cvrp`               | `{depot, customers, demands, capacities, use_roads}`| `{routes, vehicles_used, total_distance}` |
| POST   | `/compare`            | `{points}`                                         | `{results[], point_count}`        |
| GET    | `/benchmarks`         | —                                                  | `{benchmarks[]}`                  |
| GET    | `/benchmarks/{name}`  | —                                                  | `{name, description, points[]}`   |

---

## 8. Testing Strategy

| Layer          | File                     | Coverage                              |
|----------------|--------------------------|---------------------------------------|
| Unit — utils   | tests/test_algorithms.py | Haversine, distance matrix            |
| Unit — algos   | tests/test_algorithms.py | All 4 algorithms, quality, structure  |
| Integration    | tests/test_api.py        | All 7 endpoints, edge cases, errors   |

Run all tests:
```bash
cd FastRoute
pip install -r requirements.txt
python -m pytest tests/ -v
```

---

## 9. Benchmark Instances

| Name        | Points | Source          | Known Optimal |
|-------------|--------|-----------------|---------------|
| Burma 14    | 14     | Zaw Win (1977)  | 3,323 units   |
| Berlin 52   | 52     | Groetschel (1977)| 7,542 units  |
| Synthetic 20| 20     | Generated       | Unknown       |

---

## 10. Limitations & Future Work

- Path mode currently returns a straight line (no turn-by-turn routing)
- OSRM is a public API with rate limits — a self-hosted instance would be better for production
- 2-Opt can be upgraded to 3-Opt or Lin-Kernighan for better quality
- CVRP time windows (VRPTW) could be added as a dimension
- Frontend does not yet support saving/loading scenario files
