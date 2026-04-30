# 🗺 FastRoute — Route Optimisation Platform

**A university major project** demonstrating and comparing four classical route-optimisation 
algorithms on an interactive map interface.

---

## 📌 Project Summary

FastRoute solves three variants of the **Vehicle Routing Problem (VRP)**:

| Mode    | Problem                              | Algorithm Used        |
|---------|--------------------------------------|-----------------------|
| PATH    | Shortest connection between 2 points | Direct (Haversine)    |
| TSP     | Visit all stops, return to start     | OR-Tools GLS          |
| CVRP    | Multi-vehicle delivery routing       | OR-Tools + Capacity   |
| COMPARE | Benchmark all 4 algorithms at once   | NN, 2-Opt, Greedy, GLS|

---

## 🏗 Project Structure

```
FastRoute/
├── backend/
│   ├── app.py            # FastAPI REST API (7 endpoints)
│   ├── algorithms.py     # 4 custom algorithm implementations
│   ├── routing.py        # OR-Tools TSP/CVRP wrappers
│   ├── benchmarks.py     # Classic TSP benchmark instances
│   └── utils.py          # Haversine + OSRM distance matrices
├── frontend/
│   ├── index.html        # 4-mode UI layout
│   ├── map.js            # Leaflet map + all interactions
│   └── style.css         # Dark/Light theme, responsive
├── tests/
│   ├── test_algorithms.py # Unit tests — utils + all 4 algorithms
│   └── test_api.py        # Integration tests — all endpoints
├── docs/
│   └── system_design.md  # Architecture, complexity analysis, API reference
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

### Requirements
- Python **3.9+**
- `pip install -r requirements.txt`

### Step 1 — Start the backend
```bash
cd FastRoute/backend
uvicorn app:app --reload
```
Server: `http://127.0.0.1:8000`  
Docs:   `http://127.0.0.1:8000/docs` (auto-generated Swagger UI)

### Step 2 — Serve the frontend
Open a second terminal from the project root:
```bash
cd FastRoute
python -m http.server 5500
```
Open: `http://localhost:5500/frontend/index.html`

---

## 🧭 How to Use Each Mode

### PATH
1. Double-click → place **Start** (green)
2. Double-click → place **End** (red)
3. Click **⚡ Find Shortest Path**

### TSP — Travelling Salesman
1. Double-click → place **Start**
2. Double-click repeatedly → add **stops** (need ≥ 2 stops)
3. Click **⚡ Solve TSP (OR-Tools)**

### CVRP — Capacitated Vehicle Routing
1. Double-click → place **Depot** (purple)
2. Double-click → add **customers** (enter demand each time)
3. Manage fleet in sidebar — default 4 vehicles, add/remove freely
4. Each vehicle has its own editable capacity
5. Click **⚡ Solve CVRP**

> ⚠️ Total customer demand must not exceed total fleet capacity

### COMPARE — Algorithm Benchmarking
1. Load a classic benchmark (**Burma 14**, **Berlin 52**, **Synthetic 20**)  
   — or —  
   Double-click to place custom points (≥ 4)
2. Click **⚡ Run All Algorithms**
3. See ranked results table + **Distance** and **Time** bar charts
4. Best route drawn on map

---

## 🔬 Algorithms Implemented

| # | Algorithm               | Complexity      | Typical Gap |
|---|-------------------------|-----------------|-------------|
| 1 | Nearest Neighbour       | O(n²)           | ~20–25%     |
| 2 | 2-Opt Local Search      | O(n² × iter)    | ~5–10%      |
| 3 | Greedy Edge Insertion   | O(n² log n)     | ~15–20%     |
| 4 | OR-Tools GLS            | Time-limited    | ~0–3%       |

All four are implemented from scratch in `backend/algorithms.py` with full 
complexity analysis in `docs/system_design.md`.

---

## 🌐 Distance Models

| Model     | How to activate               | Description                      |
|-----------|-------------------------------|----------------------------------|
| Haversine | Default                       | Great-circle distance, instant   |
| OSRM      | Click 🛣 button in topbar     | Real road distances via OSRM API |

---

## 🧪 Running Tests

```bash
cd FastRoute
python -m pytest tests/ -v
```

Expected output: **22 tests passing** across algorithm unit tests and API integration tests.

```
tests/test_algorithms.py::test_haversine_same_point         PASSED
tests/test_algorithms.py::test_haversine_known              PASSED
tests/test_algorithms.py::test_distance_matrix_symmetric    PASSED
...
tests/test_api.py::test_health                              PASSED
tests/test_api.py::test_compare_has_all_algorithms          PASSED
...
22 passed in X.XXs
```

---

## 📡 API Reference

| Method | Endpoint             | Body                                                         |
|--------|----------------------|--------------------------------------------------------------|
| GET    | `/health`            | —                                                            |
| POST   | `/path`              | `{ "points": [[lat,lng],[lat,lng]] }`                        |
| POST   | `/tsp`               | `{ "points": [[lat,lng],...], "use_roads": false }`          |
| POST   | `/cvrp`              | `{ "depot":[lat,lng], "customers":[[lat,lng],...], "demands":[int,...], "capacities":[int,...] }` |
| POST   | `/compare`           | `{ "points": [[lat,lng],...] }`                              |
| GET    | `/benchmarks`        | —                                                            |
| GET    | `/benchmarks/{name}` | burma14 · berlin52 · random20                                |

Interactive API docs available at: `http://127.0.0.1:8000/docs`

---

## 🛠 Troubleshooting

| Problem | Solution |
|---------|----------|
| `No module named 'routing'` | Run uvicorn from **inside** `backend/` folder |
| `Failed to fetch` in browser | Backend not running — repeat Step 1 |
| CVRP returns no routes | Total demand > fleet capacity — increase caps or add vehicles |
| `pip` not found | Use `pip3` |
| Port 5500 in use | Use `python -m http.server 8080` and open `:8080` |

---

## 📚 References

1. Dantzig, G., & Ramser, J. (1959). *The Truck Dispatching Problem.* Management Science.
2. Lin, S., & Kernighan, B. (1973). *An Effective Heuristic Algorithm for the TSP.* Operations Research.
3. Google OR-Tools Documentation. https://developers.google.com/optimization
4. OSRM Project. https://project-osrm.org
5. Groetschel, M. (1977). *Polyedrische Charakterisierungen kombinatorischer Optimierungsprobleme.* (Berlin52 benchmark)

---

## 💻 Tech Stack

| Layer    | Technology                         |
|----------|------------------------------------|
| Backend  | Python 3.9+, FastAPI, Google OR-Tools |
| Frontend | Vanilla JS (ES6+), Leaflet.js      |
| Styling  | CSS custom properties, Google Fonts |
| Testing  | pytest, FastAPI TestClient         |
| Distances| Haversine (built-in), OSRM (optional) |
