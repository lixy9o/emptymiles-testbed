"""Greedy piggyback: assign each order (earliest-ready first) to the feasible existing
route that adds the least *marginal* detour, given what's already on that route.

Respects capacity, the marginal-detour cap, and a simple time check (the route must depart
inside the order's window). Marginal cost uses the same sequence-aware `sequence_detour`
the metrics layer uses, so greedy and the scorecard never disagree.

This is the simplest example of a *scorer* (it ranks routes by marginal detour). Module C
generalises that score - detour + time-slack + CO₂ delta + reason codes - behind this same
interface.
"""

from __future__ import annotations

from ..config import Config
from ..geometry import sequence_detour
from ..models import Scenario
from .base import Strategy


class Greedy(Strategy):
    name = "greedy"

    def match(self, scenario: Scenario, cfg: Config) -> dict[int, int | None]:
        assigned: dict[int, list] = {r.id: [] for r in scenario.routes}
        load: dict[int, float] = {r.id: 0.0 for r in scenario.routes}
        routes = {r.id: r for r in scenario.routes}
        assignments: dict[int, int | None] = {}

        for order in sorted(scenario.orders, key=lambda o: o.ready_time):
            best_id: int | None = None
            best_marginal = float("inf")
            for r in scenario.routes:
                if load[r.id] + order.weight_kg > r.capacity_kg:
                    continue
                if not (order.ready_time <= r.depart_time <= order.due_time):
                    continue
                base = sequence_detour(r.origin, r.dest, assigned[r.id])
                with_order = sequence_detour(r.origin, r.dest, assigned[r.id] + [order])
                marginal = with_order - base
                if marginal > cfg.max_detour_km:
                    continue
                if marginal < best_marginal:
                    best_marginal, best_id = marginal, r.id

            assignments[order.id] = best_id
            if best_id is not None:
                assigned[best_id].append(order)
                load[best_id] += order.weight_kg

        return assignments
