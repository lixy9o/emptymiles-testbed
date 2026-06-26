"""API tests. Skipped cleanly if FastAPI/httpx aren't installed, so the stdlib-only
core suite stays green without them (install with: pip install -r requirements-api.txt httpx)."""

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from api import app  # noqa: E402
from src.emptymiles_testbed.config import Config  # noqa: E402
from src.emptymiles_testbed.generator import generate  # noqa: E402
from src.emptymiles_testbed.metrics import compute  # noqa: E402
from src.emptymiles_testbed.strategies import Greedy  # noqa: E402

client = TestClient(app)


def _scenario_payload(cfg: Config) -> dict:
    """Turn a generated Scenario into the JSON the /match endpoint accepts."""
    sc = generate(cfg)
    return {
        "routes": [
            {
                "id": r.id,
                "origin": list(r.origin),
                "dest": list(r.dest),
                "capacity_kg": r.capacity_kg,
                "emissions_g_per_km": r.emissions_g_per_km,
                "cost_per_km": r.cost_per_km,
                "depart_time": r.depart_time,
            }
            for r in sc.routes
        ],
        "orders": [
            {
                "id": o.id,
                "origin": list(o.origin),
                "dest": list(o.dest),
                "weight_kg": o.weight_kg,
                "ready_time": o.ready_time,
                "due_time": o.due_time,
            }
            for o in sc.orders
        ],
        "seed": sc.seed,
    }


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_strategies_lists_all_four():
    r = client.get("/strategies")
    assert r.status_code == 200
    names = {s["name"] for s in r.json()["strategies"]}
    assert names == {"none", "greedy", "scored", "optimal"}


def test_evaluate_default_reports_baseline_and_greedy():
    r = client.post("/evaluate", json={"config": {"seed": 1, "n_orders": 30}})
    assert r.status_code == 200
    body = r.json()
    assert body["scenario"]["n_orders"] == 30
    strategies = {m["strategy"]: m for m in body["results"]}
    assert set(strategies) == {"none", "greedy"}
    # greedy should match some orders and save CO2 vs the no-matching baseline
    assert strategies["greedy"]["matched"] > 0
    assert strategies["greedy"]["co2_vs_baseline_pct"] > 0


def test_match_agrees_with_direct_metrics():
    """The API must return exactly the metrics the core library computes - no drift."""
    cfg = Config(seed=7, n_orders=40)
    payload = {"scenario": _scenario_payload(cfg), "strategy": "greedy"}
    r = client.post("/match", json=payload)
    assert r.status_code == 200
    body = r.json()

    # recompute directly from the library and compare CO2 + match count
    sc = generate(cfg)
    assignments = Greedy().match(sc, cfg)
    expected = compute(sc, assignments, cfg, 0.0, "greedy")
    assert body["metrics"]["matched"] == expected.matched
    assert body["metrics"]["co2_kg"] == pytest.approx(expected.co2_kg)


def test_match_rejects_unknown_strategy():
    cfg = Config(seed=1, n_orders=5, n_routes=5)
    r = client.post("/match", json={"scenario": _scenario_payload(cfg), "strategy": "magic"})
    assert r.status_code == 422


def test_match_rejects_empty_scenario():
    r = client.post("/match", json={"scenario": {"routes": [], "orders": []}, "strategy": "greedy"})
    assert r.status_code == 422
