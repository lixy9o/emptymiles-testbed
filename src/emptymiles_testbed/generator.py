"""Synthetic scenario generator. Deterministic for a given Config.seed.

Points are drawn either uniformly or near one of `n_clusters` hubs (controlled by
`cluster_prob`) - clustering is what makes matching viable, so it's a first-class knob.
"""

from __future__ import annotations

import random

from .config import Config
from .models import Coord, Order, PlannedRoute, Scenario


def _sample_point(rng: random.Random, cfg: Config, centers: list[Coord]) -> Coord:
    g = cfg.grid_size_km
    if centers and rng.random() < cfg.cluster_prob:
        cx, cy = rng.choice(centers)
        x = min(max(rng.gauss(cx, cfg.cluster_radius_km), 0.0), g)
        y = min(max(rng.gauss(cy, cfg.cluster_radius_km), 0.0), g)
        return (x, y)
    return (rng.uniform(0.0, g), rng.uniform(0.0, g))


def generate(cfg: Config) -> Scenario:
    rng = random.Random(cfg.seed)
    centers = [
        (rng.uniform(0.0, cfg.grid_size_km), rng.uniform(0.0, cfg.grid_size_km))
        for _ in range(cfg.n_clusters)
    ]

    routes = [
        PlannedRoute(
            id=i,
            origin=_sample_point(rng, cfg, centers),
            dest=_sample_point(rng, cfg, centers),
            capacity_kg=cfg.capacity_kg,
            emissions_g_per_km=cfg.route_emissions_g_per_km,
            cost_per_km=cfg.route_cost_per_km,
            depart_time=rng.uniform(0.0, cfg.horizon_min),
        )
        for i in range(cfg.n_routes)
    ]

    orders = []
    for j in range(cfg.n_orders):
        ready = rng.uniform(0.0, cfg.horizon_min)
        orders.append(
            Order(
                id=j,
                origin=_sample_point(rng, cfg, centers),
                dest=_sample_point(rng, cfg, centers),
                weight_kg=rng.uniform(cfg.weight_min_kg, cfg.weight_max_kg),
                ready_time=ready,
                due_time=ready + cfg.window_width_min,
            )
        )

    return Scenario(routes=routes, orders=orders, seed=cfg.seed)
