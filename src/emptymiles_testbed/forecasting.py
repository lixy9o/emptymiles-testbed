"""Module B - empty-leg forecasting.

Reload™ fills empty legs *reactively*, once a route is already running underused. This module
predicts **where and when spare capacity (empty legs) will appear**, so capacity can be
pre-positioned or orders solicited toward it *before* the trucks roll.

Forecasting only means something if there's a stable pattern to learn, so we model a `World`:
fixed hotspots, each with its own supply and demand intensity. Every "day" is a fresh random
realisation from that world (different seed), but the structure persists - some regions
reliably run spare (empty legs), others reliably short (need capacity). The forecaster learns
that structure from history and is scored against a held-out day.

Signal forecast: the **net spare-capacity field** = route capacity − order weight, aggregated
by spatial cell × departure-time bucket. Positive ⇒ empty legs likely; negative ⇒ unmet demand.
This is matcher-independent - it's about the supply/demand imbalance itself.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass, field as dfield

from .config import Config
from .models import Coord, Order, PlannedRoute, Scenario

N_CELLS = 5      # grid is split N_CELLS × N_CELLS spatially
N_BUCKETS = 4    # operating horizon split into N_BUCKETS time windows

Cell = tuple[int, int, int]  # (cell_x, cell_y, time_bucket)


# --------------------------------------------------------------------------- binning

def cell_of(coord: Coord, grid_size: float, n_cells: int = N_CELLS) -> tuple[int, int]:
    cx = min(int(coord[0] / grid_size * n_cells), n_cells - 1)
    cy = min(int(coord[1] / grid_size * n_cells), n_cells - 1)
    return (cx, cy)


def bucket_of(t: float, horizon: float, n_buckets: int = N_BUCKETS) -> int:
    return min(max(int(t / horizon * n_buckets), 0), n_buckets - 1)


def net_spare_field(
    scenario: Scenario, cfg: Config, n_cells: int = N_CELLS, n_buckets: int = N_BUCKETS
) -> dict[Cell, float]:
    """Supply (route capacity) minus demand (order weight) per cell × time bucket."""
    f: dict[Cell, float] = defaultdict(float)
    for r in scenario.routes:
        key = (*cell_of(r.origin, cfg.grid_size_km, n_cells), bucket_of(r.depart_time, cfg.horizon_min, n_buckets))
        f[key] += r.capacity_kg
    for o in scenario.orders:
        key = (*cell_of(o.origin, cfg.grid_size_km, n_cells), bucket_of(o.ready_time, cfg.horizon_min, n_buckets))
        f[key] -= o.weight_kg
    return dict(f)


# ------------------------------------------------------------------- the stable world

@dataclass
class World:
    """A persistent demand/supply geography. Days vary; this doesn't."""

    centers: list[Coord]
    supply_w: list[float]   # relative likelihood a route originates near each center
    demand_w: list[float]   # relative likelihood an order originates near each center


def make_world(cfg: Config, world_seed: int) -> World:
    rng = random.Random(world_seed)
    g = cfg.grid_size_km
    centers = [(rng.uniform(0, g), rng.uniform(0, g)) for _ in range(cfg.n_clusters)]
    supply_w = [rng.random() + 0.1 for _ in range(cfg.n_clusters)]
    demand_w = [rng.random() + 0.1 for _ in range(cfg.n_clusters)]
    return World(centers=centers, supply_w=supply_w, demand_w=demand_w)


def _near(rng: random.Random, center: Coord, cfg: Config) -> Coord:
    g = cfg.grid_size_km
    x = min(max(rng.gauss(center[0], cfg.cluster_radius_km), 0.0), g)
    y = min(max(rng.gauss(center[1], cfg.cluster_radius_km), 0.0), g)
    return (x, y)


def sample_day(world: World, cfg: Config, day_seed: int) -> Scenario:
    """One stochastic day drawn from a fixed `world` - same structure, fresh realisation."""
    rng = random.Random(day_seed)
    routes = []
    for i in range(cfg.n_routes):
        origin_c = rng.choices(world.centers, weights=world.supply_w, k=1)[0]
        routes.append(
            PlannedRoute(
                id=i,
                origin=_near(rng, origin_c, cfg),
                dest=_near(rng, rng.choice(world.centers), cfg),
                capacity_kg=cfg.capacity_kg,
                emissions_g_per_km=cfg.route_emissions_g_per_km,
                cost_per_km=cfg.route_cost_per_km,
                depart_time=rng.uniform(0.0, cfg.horizon_min),
            )
        )
    orders = []
    for j in range(cfg.n_orders):
        origin_c = rng.choices(world.centers, weights=world.demand_w, k=1)[0]
        ready = rng.uniform(0.0, cfg.horizon_min)
        orders.append(
            Order(
                id=j,
                origin=_near(rng, origin_c, cfg),
                dest=_near(rng, rng.choice(world.centers), cfg),
                weight_kg=rng.uniform(cfg.weight_min_kg, cfg.weight_max_kg),
                ready_time=ready,
                due_time=ready + cfg.window_width_min,
            )
        )
    return Scenario(routes=routes, orders=orders, seed=day_seed)


# ----------------------------------------------------------------------- forecaster

@dataclass
class EmptyLegForecaster:
    """Empirical-mean forecaster: the expected spare-capacity field, learned from history.

    Deliberately simple and inspectable (no hidden ML). The upgrade path - gradient boosting
    or a spatiotemporal model on the same field - slots in behind `fit`/`predict` unchanged.
    """

    cfg: Config
    n_cells: int = N_CELLS
    n_buckets: int = N_BUCKETS
    field: dict[Cell, float] = dfield(default_factory=dict)

    def fit(self, scenarios: list[Scenario]) -> "EmptyLegForecaster":
        agg: dict[Cell, float] = defaultdict(float)
        for s in scenarios:
            for k, v in net_spare_field(s, self.cfg, self.n_cells, self.n_buckets).items():
                agg[k] += v
        n = len(scenarios) or 1
        self.field = {k: v / n for k, v in agg.items()}
        return self

    def predict(self) -> dict[Cell, float]:
        return dict(self.field)

    def hotspots(self, k: int = 5):
        """Top-k predicted empty-leg cells (most spare) and top-k deficit cells (most short)."""
        spare = sorted(self.field.items(), key=lambda kv: kv[1], reverse=True)[:k]
        deficit = sorted(self.field.items(), key=lambda kv: kv[1])[:k]
        return spare, deficit


# ----------------------------------------------------------------------- evaluation

@dataclass
class ForecastEval:
    rmse: float           # root-mean-squared error of the forecast field vs the actual day
    baseline_rmse: float  # RMSE of the no-skill baseline (predict "no imbalance anywhere")
    skill: float          # 1 - rmse/baseline_rmse: fraction of error the forecast removes
    precision_at_k: float # share of predicted top-k spare cells that were actually top-k
    k: int


def evaluate(forecaster: EmptyLegForecaster, actual: Scenario, k: int = 5) -> ForecastEval:
    """Scored with RMSE, not MAE: the field is lumpy and mostly-zero per day, so absolute
    error would reward predicting zero everywhere. The empirical-mean forecast minimises
    *squared* error, so RMSE is both the principled and the fair comparison - it beats the
    no-skill baseline by exactly the squared signal (μ²) it captures."""
    pred = forecaster.predict()
    actual_field = net_spare_field(actual, forecaster.cfg, forecaster.n_cells, forecaster.n_buckets)
    keys = set(pred) | set(actual_field)
    n = len(keys)

    rmse = math.sqrt(sum((pred.get(c, 0.0) - actual_field.get(c, 0.0)) ** 2 for c in keys) / n)
    baseline_rmse = math.sqrt(sum(actual_field.get(c, 0.0) ** 2 for c in keys) / n)
    skill = 1.0 - rmse / baseline_rmse if baseline_rmse else 0.0

    pred_top = {c for c, _ in sorted(pred.items(), key=lambda kv: kv[1], reverse=True)[:k]}
    actual_top = {c for c, _ in sorted(actual_field.items(), key=lambda kv: kv[1], reverse=True)[:k]}
    precision = len(pred_top & actual_top) / k if k else 0.0

    return ForecastEval(rmse=rmse, baseline_rmse=baseline_rmse, skill=skill, precision_at_k=precision, k=k)
