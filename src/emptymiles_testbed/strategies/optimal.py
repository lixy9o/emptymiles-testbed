"""Optimal matcher - a CO₂-minimising assignment solved with OR-Tools CP-SAT.

It optimises the *independent-insertion* relaxation (each order costed against a route's
base leg, capacity enforced per route). That makes the objective linear and exactly
solvable, and gives a principled **ceiling**: how much could matching save if you assigned
perfectly under that cost model? The metrics layer then reports the *realised*,
sequence-aware cost of the chosen assignment - so any gap between the two is visible.

Doubles as a correctness oracle on small instances. Requires `pip install ortools`.
"""

from __future__ import annotations

from ..config import Config
from ..geometry import distance, insertion_detour
from ..models import Scenario
from .base import Strategy

try:  # optional dependency
    from ortools.sat.python import cp_model
except ImportError:  # pragma: no cover
    cp_model = None


class Optimal(Strategy):
    name = "optimal"

    def match(self, scenario: Scenario, cfg: Config) -> dict[int, int | None]:
        if cp_model is None:  # pragma: no cover
            raise RuntimeError("The optimal matcher needs OR-Tools: pip install ortools")

        model = cp_model.CpModel()
        routes = {r.id: r for r in scenario.routes}
        x: dict[tuple[int, int], object] = {}  # (order_id, route_id) -> BoolVar

        for o in scenario.orders:
            for r in scenario.routes:
                if o.weight_kg > r.capacity_kg:
                    continue
                if not (o.ready_time <= r.depart_time <= o.due_time):
                    continue
                if insertion_detour(r, o) > cfg.max_detour_km:
                    continue
                x[(o.id, r.id)] = model.NewBoolVar(f"x_{o.id}_{r.id}")

        # each order matched to at most one route
        for o in scenario.orders:
            vars_o = [x[(o.id, r.id)] for r in scenario.routes if (o.id, r.id) in x]
            if vars_o:
                model.Add(sum(vars_o) <= 1)

        # capacity per route (weights rounded to int kg for CP-SAT)
        for r in scenario.routes:
            terms = [
                int(round(o.weight_kg)) * x[(o.id, r.id)]
                for o in scenario.orders
                if (o.id, r.id) in x
            ]
            if terms:
                model.Add(sum(terms) <= int(round(r.capacity_kg)))

        # maximise CO₂ saved vs. the dedicated-trip baseline (g, rounded to int)
        terms = []
        for (oid, rid), var in x.items():
            o = next(o for o in scenario.orders if o.id == oid)
            r = routes[rid]
            dedicated = (distance(o.origin, o.dest) + distance(o.dest, o.origin)) * cfg.dedicated_emissions_g_per_km
            matched = insertion_detour(r, o) * r.emissions_g_per_km
            terms.append(int(round(dedicated - matched)) * var)
        model.Maximize(sum(terms))

        solver = cp_model.CpSolver()
        solver.Solve(model)

        assignments: dict[int, int | None] = {o.id: None for o in scenario.orders}
        for (oid, rid), var in x.items():
            if solver.Value(var) == 1:
                assignments[oid] = rid
        return assignments
