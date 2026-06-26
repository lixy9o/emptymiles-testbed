"""Metrics are the single source of truth - recomputed purely from a strategy's
assignment mapping, so two strategies are always compared on identical accounting.

Distance accounting:
  - Planned routes' base origin→dest km happen in every scenario (constant across
    strategies) and are counted once.
  - *Matched* orders on a route are costed together via `sequence_detour` (sequence-aware:
    insertions compound), replayed in ready-time order so the cost is strategy-independent.
  - An *unmatched* order is a dedicated trip: outbound + an empty return leg. The empty
    return is the empty-mile penalty matching exists to avoid.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .config import Config
from .geometry import distance, sequence_detour
from .models import Scenario


@dataclass
class Metrics:
    strategy: str
    matched: int
    total_orders: int
    base_route_km: float
    detour_km: float
    dedicated_km: float
    empty_km: float
    total_km: float
    co2_kg: float
    cost: float
    latency_ms: float

    @property
    def match_rate(self) -> float:
        return self.matched / self.total_orders if self.total_orders else 0.0


def compute(
    scenario: Scenario,
    assignments: dict[int, int | None],
    cfg: Config,
    latency_ms: float,
    name: str,
) -> Metrics:
    routes = {r.id: r for r in scenario.routes}
    orders = {o.id: o for o in scenario.orders}

    base_route_km = sum(distance(r.origin, r.dest) for r in scenario.routes)
    co2_g = sum(distance(r.origin, r.dest) * r.emissions_g_per_km for r in scenario.routes)
    cost = sum(distance(r.origin, r.dest) * r.cost_per_km for r in scenario.routes)

    # group matched orders by route, so we can cost them as a compounding sequence
    on_route: dict[int, list] = defaultdict(list)
    dedicated_km = empty_km = 0.0
    matched = 0

    for oid, rid in assignments.items():
        o = orders[oid]
        if rid is not None:
            on_route[rid].append(o)
            matched += 1
        else:
            out = distance(o.origin, o.dest)
            back = distance(o.dest, o.origin)  # empty return leg
            dedicated_km += out + back
            empty_km += back
            co2_g += (out + back) * cfg.dedicated_emissions_g_per_km
            cost += (out + back) * cfg.dedicated_cost_per_km

    detour_km = 0.0
    for rid, assigned in on_route.items():
        r = routes[rid]
        d = sequence_detour(r.origin, r.dest, assigned)
        detour_km += d
        co2_g += d * r.emissions_g_per_km
        cost += d * r.cost_per_km

    return Metrics(
        strategy=name,
        matched=matched,
        total_orders=len(scenario.orders),
        base_route_km=base_route_km,
        detour_km=detour_km,
        dedicated_km=dedicated_km,
        empty_km=empty_km,
        total_km=base_route_km + detour_km + dedicated_km,
        co2_kg=co2_g / 1000.0,
        cost=cost,
        latency_ms=latency_ms,
    )
