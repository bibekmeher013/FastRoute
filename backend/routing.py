"""
routing.py — Road-aware route solvers
Uses OSRM to fetch real road geometry for all modes.
Falls back to straight lines if OSRM is unreachable.
"""
import json
import urllib.request
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from utils import create_distance_matrix, create_osrm_matrix

OSRM_BASE = "https://router.project-osrm.org"


# ── OSRM road geometry helpers ────────────────────────────────────────────────

def _osrm_route_geometry(start, end, timeout=8):
    """
    Fetch actual road polyline from OSRM between two [lat,lng] points.
    Returns list of [lat, lng] waypoints following real roads.
    Falls back to [start, end] straight line on failure.
    """
    lng1, lat1 = start[1], start[0]
    lng2, lat2 = end[1],   end[0]
    url = (f"{OSRM_BASE}/route/v1/driving/"
           f"{lng1},{lat1};{lng2},{lat2}"
           f"?geometries=geojson&overview=full&steps=false")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FastRoute/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        if data.get("code") == "Ok":
            coords = data["routes"][0]["geometry"]["coordinates"]
            # OSRM returns [lng, lat] — flip to [lat, lng] for Leaflet
            return [[c[1], c[0]] for c in coords]
    except Exception:
        pass
    return [start, end]   # fallback straight line


def _stitch_road_segments(waypoints, timeout=8):
    """
    Given an ordered list of [lat,lng] waypoints, fetch road geometry
    for each consecutive pair and stitch them into one continuous polyline.
    """
    full_route = []
    for i in range(len(waypoints) - 1):
        seg = _osrm_route_geometry(waypoints[i], waypoints[i + 1], timeout)
        # avoid duplicating the junction point between segments
        if full_route and seg:
            seg = seg[1:]
        full_route.extend(seg)
    return full_route


def _osrm_road_distance_m(start, end, timeout=8):
    """Return driving distance in metres between two points via OSRM."""
    lng1, lat1 = start[1], start[0]
    lng2, lat2 = end[1],   end[0]
    url = (f"{OSRM_BASE}/route/v1/driving/"
           f"{lng1},{lat1};{lng2},{lat2}"
           f"?overview=false")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FastRoute/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        if data.get("code") == "Ok":
            return int(data["routes"][0]["distance"])
    except Exception:
        pass
    return None


# ── PATH ──────────────────────────────────────────────────────────────────────

def solve_path(start, end):
    """
    Return the actual road route between start and end using OSRM.
    Falls back to a straight line if OSRM is unavailable.
    """
    road_coords = _osrm_route_geometry(start, end)
    used_roads = len(road_coords) > 2

    # calculate distance along the returned geometry
    dist = 0.0
    import math
    for i in range(len(road_coords) - 1):
        a, b = road_coords[i], road_coords[i + 1]
        dlat = math.radians(b[0] - a[0])
        dlng = math.radians(b[1] - a[1])
        x = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(a[0])) *
             math.cos(math.radians(b[0])) *
             math.sin(dlng / 2) ** 2)
        dist += 6371 * 2 * math.atan2(math.sqrt(x), math.sqrt(1 - x))

    return {
        "route": road_coords,
        "distance": round(dist, 3),
        "used_roads": used_roads,
    }


# ── TSP ───────────────────────────────────────────────────────────────────────

def solve_tsp(points, use_roads=False):
    """
    Solve TSP with OR-Tools, then stitch road geometry between stops.
    """
    matrix = create_osrm_matrix(points) if use_roads else create_distance_matrix(points)
    n = len(points)

    manager = pywrapcp.RoutingIndexManager(n, 1, 0)
    routing  = pywrapcp.RoutingModel(manager)

    def dist_cb(fi, ti):
        return matrix[manager.IndexToNode(fi)][manager.IndexToNode(ti)]

    cb = routing.RegisterTransitCallback(dist_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(cb)

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    params.time_limit.seconds = 5

    sol = routing.SolveWithParameters(params)
    if not sol:
        return {"route": [], "distance": 0}

    tour, idx = [], routing.Start(0)
    while not routing.IsEnd(idx):
        tour.append(manager.IndexToNode(idx))
        idx = sol.Value(routing.NextVar(idx))
    tour.append(tour[0])   # close tour

    ordered_waypoints = [points[i] for i in tour]
    dist_m = sum(matrix[tour[i]][tour[i + 1]] for i in range(len(tour) - 1))

    # stitch actual road geometry between each consecutive waypoint
    road_route = _stitch_road_segments(ordered_waypoints)

    return {
        "route": road_route,
        "waypoints": ordered_waypoints,
        "distance": round(dist_m / 1000, 3),
        "used_roads": use_roads,
    }


# ── CVRP ──────────────────────────────────────────────────────────────────────

def solve_cvrp(depot, customers, demands, capacities, use_roads=False):
    """
    Solve CVRP with OR-Tools + per-vehicle capacities.
    Each vehicle route is stitched with real road geometry.
    """
    num_vehicles = len(capacities)
    locations    = [depot] + customers
    full_demands = [0] + demands

    matrix = create_osrm_matrix(locations) if use_roads else create_distance_matrix(locations)

    manager = pywrapcp.RoutingIndexManager(len(locations), num_vehicles, 0)
    routing  = pywrapcp.RoutingModel(manager)

    def dist_cb(fi, ti):
        return matrix[manager.IndexToNode(fi)][manager.IndexToNode(ti)]

    tc = routing.RegisterTransitCallback(dist_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(tc)

    def demand_cb(fi):
        return full_demands[manager.IndexToNode(fi)]

    dc = routing.RegisterUnaryTransitCallback(demand_cb)
    routing.AddDimensionWithVehicleCapacity(dc, 0, capacities, True, "Capacity")

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    params.time_limit.seconds = 10

    sol = routing.SolveWithParameters(params)
    if not sol:
        return {"routes": [], "total_distance": 0, "vehicles_used": 0}

    routes      = []
    total_dist  = 0
    loc_idx     = {tuple(p): i for i, p in enumerate(locations)}

    for vid in range(num_vehicles):
        idx        = routing.Start(vid)
        stop_indices = []
        while not routing.IsEnd(idx):
            stop_indices.append(manager.IndexToNode(idx))
            idx = sol.Value(routing.NextVar(idx))
        stop_indices.append(0)   # return to depot

        if len(stop_indices) <= 2:
            continue  # idle vehicle — skip

        waypoints  = [locations[i] for i in stop_indices]
        # stitch road geometry for this vehicle's route
        road_route = _stitch_road_segments(waypoints)

        # accumulate distance
        seg_dist = sum(
            matrix[stop_indices[i]][stop_indices[i + 1]]
            for i in range(len(stop_indices) - 1)
        )
        total_dist += seg_dist
        routes.append(road_route)

    return {
        "routes":         routes,
        "total_distance": round(total_dist / 1000, 3),
        "vehicles_used":  len(routes),
    }


# ── Road geometry stitching (exported for use in app.py) ─────────────────────

def stitch_route(waypoints):
    """
    Given ordered [lat,lng] waypoints from any algorithm,
    return a road-following polyline via OSRM.
    Falls back to straight segments if OSRM is unavailable.
    """
    return _stitch_road_segments(waypoints)
