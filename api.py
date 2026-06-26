"""HTTP API for the EmptyMiles matching testbed (FastAPI).

The same matcher interface, metrics, and synthetic generator the CLI/dashboard use,
exposed as a small service so other code can call it - the shape a real
model-evaluation system takes once it leaves a notebook.

Two endpoints tell the whole story:
  POST /evaluate - generate a synthetic scenario from a Config and benchmark one or
                   more strategies on it. No data needed: hit it and get numbers.
  POST /match    - bring your own scenario (routes + orders), run one strategy, get the
                   assignment mapping back plus the same honest, recomputed metrics.

Run locally:  uvicorn api:app --reload   then open  http://localhost:8000/docs
"""

from __future__ import annotations

import time
from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from src.emptymiles_testbed.config import Config
from src.emptymiles_testbed.generator import generate
from src.emptymiles_testbed.metrics import Metrics, compute
from src.emptymiles_testbed.models import Order, PlannedRoute, Scenario
from src.emptymiles_testbed.strategies import Greedy, NoMatching, Optimal, ScoredGreedy, Strategy

# name -> constructor. `optimal` needs OR-Tools at call time; the import itself is safe.
STRATEGIES: dict[str, type[Strategy]] = {
    "none": NoMatching,
    "greedy": Greedy,
    "scored": ScoredGreedy,
    "optimal": Optimal,
}


def _ortools_available() -> bool:
    try:
        import ortools  # noqa: F401

        return True
    except ImportError:
        return False


app = FastAPI(
    title="EmptyMiles Matching Testbed API",
    version="1.0.0",
    description=(
        "Offline evaluation harness for delivery-matching strategies. "
        "Generate synthetic logistics scenarios or POST your own, run a matching "
        "strategy, and get fill rate / empty-mile % / CO2 vs. baseline / cost / latency "
        "on identical, reproducible accounting."
    ),
)


# --------------------------------------------------------------------------- I/O models


class ConfigIn(BaseModel):
    """Any Config knob you want to override; omitted fields fall back to defaults."""

    seed: int | None = None
    grid_size_km: float | None = None
    n_routes: int | None = None
    n_orders: int | None = None
    n_clusters: int | None = None
    cluster_prob: float | None = None
    cluster_radius_km: float | None = None
    capacity_kg: float | None = None
    weight_min_kg: float | None = None
    weight_max_kg: float | None = None
    max_detour_km: float | None = None
    horizon_min: float | None = None
    window_width_min: float | None = None
    route_emissions_g_per_km: float | None = None
    dedicated_emissions_g_per_km: float | None = None
    route_cost_per_km: float | None = None
    dedicated_cost_per_km: float | None = None

    def to_config(self) -> Config:
        overrides = {k: v for k, v in self.model_dump().items() if v is not None}
        return Config(**{**asdict(Config()), **overrides})


class RouteIn(BaseModel):
    id: int
    origin: tuple[float, float] = Field(..., description="[x, y] in km on the grid")
    dest: tuple[float, float]
    capacity_kg: float
    emissions_g_per_km: float
    cost_per_km: float
    depart_time: float


class OrderIn(BaseModel):
    id: int
    origin: tuple[float, float]
    dest: tuple[float, float]
    weight_kg: float
    ready_time: float
    due_time: float


class ScenarioIn(BaseModel):
    routes: list[RouteIn]
    orders: list[OrderIn]
    seed: int = 0

    def to_scenario(self) -> Scenario:
        return Scenario(
            routes=[
                PlannedRoute(
                    id=r.id,
                    origin=r.origin,
                    dest=r.dest,
                    capacity_kg=r.capacity_kg,
                    emissions_g_per_km=r.emissions_g_per_km,
                    cost_per_km=r.cost_per_km,
                    depart_time=r.depart_time,
                )
                for r in self.routes
            ],
            orders=[
                Order(
                    id=o.id,
                    origin=o.origin,
                    dest=o.dest,
                    weight_kg=o.weight_kg,
                    ready_time=o.ready_time,
                    due_time=o.due_time,
                )
                for o in self.orders
            ],
            seed=self.seed,
        )


class MetricsOut(BaseModel):
    strategy: str
    matched: int
    total_orders: int
    match_rate: float
    base_route_km: float
    detour_km: float
    dedicated_km: float
    empty_km: float
    total_km: float
    co2_kg: float
    cost: float
    latency_ms: float
    co2_vs_baseline_pct: float | None = None

    @classmethod
    def from_metrics(cls, m: Metrics, baseline_co2: float | None = None) -> "MetricsOut":
        saving = None
        if baseline_co2:
            saving = (1 - m.co2_kg / baseline_co2) * 100
        return cls(
            strategy=m.strategy,
            matched=m.matched,
            total_orders=m.total_orders,
            match_rate=m.match_rate,
            base_route_km=m.base_route_km,
            detour_km=m.detour_km,
            dedicated_km=m.dedicated_km,
            empty_km=m.empty_km,
            total_km=m.total_km,
            co2_kg=m.co2_kg,
            cost=m.cost,
            latency_ms=m.latency_ms,
            co2_vs_baseline_pct=saving,
        )


class EvaluateRequest(BaseModel):
    config: ConfigIn | None = None
    strategies: list[str] | None = Field(
        default=None, description="Strategy names to run; defaults to ['none', 'greedy']."
    )


class ScenarioSummary(BaseModel):
    n_routes: int
    n_orders: int
    seed: int


class EvaluateResponse(BaseModel):
    scenario: ScenarioSummary
    results: list[MetricsOut]


class MatchRequest(BaseModel):
    scenario: ScenarioIn
    strategy: str = "greedy"
    config: ConfigIn | None = None


class MatchResponse(BaseModel):
    strategy: str
    assignments: dict[int, int | None] = Field(
        ..., description="order_id -> route_id, or null for a dedicated trip"
    )
    metrics: MetricsOut


# ----------------------------------------------------------------------------- helpers


def _resolve(name: str) -> Strategy:
    if name not in STRATEGIES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown strategy '{name}'. Choose from {sorted(STRATEGIES)}.",
        )
    if name == "optimal" and not _ortools_available():
        raise HTTPException(
            status_code=501,
            detail="The 'optimal' strategy needs OR-Tools, which is not installed in this deployment.",
        )
    return STRATEGIES[name]()


def _run(
    strategy: Strategy, scenario: Scenario, cfg: Config
) -> tuple[Metrics, dict[int, int | None]]:
    t0 = time.perf_counter()
    assignments = strategy.match(scenario, cfg)
    latency_ms = (time.perf_counter() - t0) * 1000.0
    return compute(scenario, assignments, cfg, latency_ms, strategy.name), assignments


# ------------------------------------------------------------------------------ routes


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/strategies")
def strategies() -> dict[str, list[dict[str, object]]]:
    out = []
    for name in STRATEGIES:
        available = name != "optimal" or _ortools_available()
        out.append({"name": name, "available": available})
    return {"strategies": out}


@app.post("/evaluate", response_model=EvaluateResponse)
def evaluate(req: EvaluateRequest) -> EvaluateResponse:
    """Generate a synthetic scenario and benchmark strategies on it."""
    cfg = (req.config or ConfigIn()).to_config()
    names = req.strategies or ["none", "greedy"]
    strats = [_resolve(n) for n in names]

    scenario = generate(cfg)
    metrics_by_name: dict[str, Metrics] = {}
    for s in strats:
        m, _ = _run(s, scenario, cfg)
        metrics_by_name[s.name] = m

    baseline_co2 = metrics_by_name["none"].co2_kg if "none" in metrics_by_name else None
    return EvaluateResponse(
        scenario=ScenarioSummary(
            n_routes=len(scenario.routes), n_orders=len(scenario.orders), seed=scenario.seed
        ),
        results=[MetricsOut.from_metrics(m, baseline_co2) for m in metrics_by_name.values()],
    )


@app.post("/match", response_model=MatchResponse)
def match(req: MatchRequest) -> MatchResponse:
    """Run one strategy on a scenario you supply; get assignments + metrics back."""
    scenario = req.scenario.to_scenario()
    if not scenario.routes or not scenario.orders:
        raise HTTPException(status_code=422, detail="Scenario needs at least one route and one order.")
    cfg = (req.config or ConfigIn()).to_config()
    strategy = _resolve(req.strategy)

    m, assignments = _run(strategy, scenario, cfg)
    return MatchResponse(
        strategy=strategy.name,
        assignments=assignments,
        metrics=MetricsOut.from_metrics(m),
    )
