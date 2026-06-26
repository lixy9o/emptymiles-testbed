"""Module C - match-quality scoring with reason codes.

Greedy ranks candidate routes by one number (marginal detour). A real dispatcher - and a
real algorithm you can tune - wants to know *why* a match is good, and to weigh competing
signals. `Scorer` turns each (order, route) candidate into a `MatchScore` that carries:

  - a single comparable `score` (higher = better),
  - the component signals behind it (CO₂ saved, detour, capacity fit, time slack),
  - `feasible` + plain-English `reasons` - including *why* an infeasible candidate was rejected.

The weights are explicit and adjustable, so "the matcher prefers X over Y" is a number you
can point at, not a black box. This plugs into the same `Strategy` interface via `ScoredGreedy`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import Config
from .geometry import distance, sequence_detour
from .models import Order, PlannedRoute


@dataclass
class MatchScore:
    order_id: int
    route_id: int
    feasible: bool
    score: float
    marginal_detour_km: float
    time_slack_min: float
    utilisation: float        # route load after this order / capacity
    co2_saved_kg: float       # vs. giving the order a dedicated trip
    reasons: list[str] = field(default_factory=list)


@dataclass
class Scorer:
    """Weights are the tuning surface. Defaults prioritise CO₂ saved (the real objective),
    reward filling a vehicle, and lightly prefer shorter detours / more time slack."""

    cfg: Config
    w_co2: float = 1.0       # per kg CO₂ saved
    w_util: float = 0.5      # per unit capacity utilisation (0..1)
    w_detour: float = 0.2    # per km of marginal detour (penalty)
    w_slack: float = 0.01    # per minute of schedule slack

    def score(
        self,
        route: PlannedRoute,
        current_orders: list[Order],
        current_load: float,
        order: Order,
    ) -> MatchScore:
        cfg = self.cfg

        time_ok = order.ready_time <= route.depart_time <= order.due_time
        new_load = current_load + order.weight_kg
        cap_ok = new_load <= route.capacity_kg

        base = sequence_detour(route.origin, route.dest, current_orders)
        with_order = sequence_detour(route.origin, route.dest, current_orders + [order])
        marginal = with_order - base
        detour_ok = marginal <= cfg.max_detour_km

        dedicated_g = (
            distance(order.origin, order.dest) + distance(order.dest, order.origin)
        ) * cfg.dedicated_emissions_g_per_km
        matched_g = marginal * route.emissions_g_per_km
        co2_saved_kg = (dedicated_g - matched_g) / 1000.0
        utilisation = new_load / route.capacity_kg
        slack = min(route.depart_time - order.ready_time, order.due_time - route.depart_time)

        blockers: list[str] = []
        if not time_ok:
            blockers.append("route departs outside the order's time window")
        if not cap_ok:
            blockers.append(f"over capacity ({new_load:.0f} > {route.capacity_kg:.0f} kg)")
        if not detour_ok:
            blockers.append(f"detour {marginal:.1f} km exceeds the {cfg.max_detour_km:.0f} km cap")
        # carbon guard: never make a match that emits more than a dedicated trip would.
        # Capacity utilisation is only ever a tie-breaker *among* carbon-positive matches.
        if co2_saved_kg < 0:
            blockers.append(f"would emit more than a dedicated trip ({co2_saved_kg:.1f} kg CO₂)")

        if blockers:
            return MatchScore(
                order.id, route.id, False, float("-inf"),
                marginal, slack if time_ok else 0.0, utilisation, co2_saved_kg, blockers,
            )

        score = (
            self.w_co2 * co2_saved_kg
            - self.w_detour * marginal
            + self.w_util * utilisation
            + self.w_slack * slack
        )
        reasons = [
            f"saves {co2_saved_kg:.1f} kg CO₂ vs a dedicated trip",
            f"adds only {marginal:.1f} km detour",
            f"fills the route to {utilisation * 100:.0f}% capacity",
            f"{slack:.0f} min of schedule slack",
        ]
        return MatchScore(
            order.id, route.id, True, score,
            marginal, slack, utilisation, co2_saved_kg, reasons,
        )
