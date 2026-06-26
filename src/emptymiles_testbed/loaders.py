"""Replay hook - build a Scenario from real CSV logs. The same harness that runs synthetic
scenarios runs your actual data the day it's shared. This is the bridge from "Yumna's
sim" to "a tool the team uses."

Expected CSV headers
  routes: id, ox, oy, dx, dy, capacity_kg, emissions_g_per_km, cost_per_km, depart_time
  orders: id, ox, oy, dx, dy, weight_kg, ready_time, due_time

Coordinates are whatever unit `geometry.distance` expects (km on the grid today; swap for
projected road coordinates when `distance` becomes road-aware).
"""

from __future__ import annotations

import csv

from .models import Order, PlannedRoute, Scenario


def _rows(path: str) -> list[dict[str, str]]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def scenario_from_csv(routes_csv: str, orders_csv: str, seed: int = 0) -> Scenario:
    routes = [
        PlannedRoute(
            id=int(r["id"]),
            origin=(float(r["ox"]), float(r["oy"])),
            dest=(float(r["dx"]), float(r["dy"])),
            capacity_kg=float(r["capacity_kg"]),
            emissions_g_per_km=float(r["emissions_g_per_km"]),
            cost_per_km=float(r["cost_per_km"]),
            depart_time=float(r["depart_time"]),
        )
        for r in _rows(routes_csv)
    ]
    orders = [
        Order(
            id=int(o["id"]),
            origin=(float(o["ox"]), float(o["oy"])),
            dest=(float(o["dx"]), float(o["dy"])),
            weight_kg=float(o["weight_kg"]),
            ready_time=float(o["ready_time"]),
            due_time=float(o["due_time"]),
        )
        for o in _rows(orders_csv)
    ]
    return Scenario(routes=routes, orders=orders, seed=seed)
