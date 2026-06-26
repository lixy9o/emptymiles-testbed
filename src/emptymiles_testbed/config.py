"""All tunable knobs in one seeded, JSON-loadable place. Every run is reproducible from
its Config alone."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from .emissions import DEFAULT_COST_PER_KM, VAN_G_PER_KM


@dataclass
class Config:
    seed: int = 42

    # --- network shape (module D explores these) ---
    grid_size_km: float = 50.0
    n_routes: int = 40
    n_orders: int = 60
    n_clusters: int = 5
    cluster_prob: float = 0.6       # P(a point is drawn near a cluster vs. uniform)
    cluster_radius_km: float = 6.0

    # --- order/vehicle physical params ---
    capacity_kg: float = 1000.0
    weight_min_kg: float = 50.0
    weight_max_kg: float = 400.0

    # --- matching feasibility ---
    max_detour_km: float = 8.0
    horizon_min: float = 480.0      # 8-hour operating window
    window_width_min: float = 120.0

    # --- emission & cost factors (see emissions.py) ---
    route_emissions_g_per_km: float = VAN_G_PER_KM
    dedicated_emissions_g_per_km: float = VAN_G_PER_KM
    route_cost_per_km: float = DEFAULT_COST_PER_KM
    dedicated_cost_per_km: float = DEFAULT_COST_PER_KM

    @classmethod
    def from_json(cls, path: str) -> "Config":
        with open(path) as f:
            return cls(**json.load(f))

    def to_json(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)

    def replace(self, **overrides) -> "Config":
        """Return a copy with some fields overridden (used by parameter sweeps)."""
        return Config(**{**asdict(self), **overrides})
