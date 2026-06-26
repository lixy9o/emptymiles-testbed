"""Geometry helpers shared by strategies and metrics, so both compute detours the same way.

`distance()` is the single swap point for real road-network distances (phase 2): replace the
Euclidean body, or route through `road_distance()`, and nothing else changes.
"""

from __future__ import annotations

import math

from .models import Coord, Order, PlannedRoute


def distance(a: Coord, b: Coord) -> float:
    """Euclidean distance in km (grid world). The one place to swap in road distances."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def road_distance(a: Coord, b: Coord) -> float:  # pragma: no cover - phase-2 extension point
    """Phase-2 hook: real road-network distance (e.g. OSMnx/NetworkX shortest path).
    Left unimplemented so the dependency stays optional until we need it."""
    raise NotImplementedError("Road-network distances are a phase-2 upgrade (see README).")


def route_length(points: list[Coord]) -> float:
    return sum(distance(points[i], points[i + 1]) for i in range(len(points) - 1))


def _insert_point(waypoints: list[Coord], p: Coord, lo: int) -> tuple[list[Coord], int, float]:
    """Insert `p` at the cheapest position at index >= `lo` (endpoints stay fixed)."""
    best_added = float("inf")
    best_k = lo
    for k in range(lo, len(waypoints)):
        added = (
            distance(waypoints[k - 1], p)
            + distance(p, waypoints[k])
            - distance(waypoints[k - 1], waypoints[k])
        )
        if added < best_added:
            best_added, best_k = added, k
    new = waypoints[:best_k] + [p] + waypoints[best_k:]
    return new, best_k, best_added


def insert_pair(waypoints: list[Coord], pickup: Coord, dropoff: Coord) -> tuple[list[Coord], float]:
    """Insert pickup then dropoff (dropoff must come after pickup). Cheapest sequential
    insertion - a small, documented relaxation of jointly-optimal insertion."""
    wp, kp, a1 = _insert_point(waypoints, pickup, lo=1)
    wp, _, a2 = _insert_point(wp, dropoff, lo=kp + 1)
    return wp, a1 + a2


def sequence_detour(origin: Coord, dest: Coord, orders: list[Order]) -> float:
    """Total extra km to serve all `orders` on a route origin→dest, inserting them in
    ready-time order. Sequence-aware: each insertion compounds on the previous ones.
    This is the realism upgrade over costing every order against the bare base leg."""
    waypoints = [origin, dest]
    for o in sorted(orders, key=lambda x: x.ready_time):
        waypoints, _ = insert_pair(waypoints, o.origin, o.dest)
    return route_length(waypoints) - distance(origin, dest)


def insertion_detour(route: PlannedRoute, order: Order) -> float:
    """Independent (non-compounding) detour for a single order against a route's base leg.
    Kept for the optimal matcher's linear objective, which optimises this relaxation."""
    base = distance(route.origin, route.dest)
    via = (
        distance(route.origin, order.origin)
        + distance(order.origin, order.dest)
        + distance(order.dest, route.dest)
    )
    return max(0.0, via - base)
