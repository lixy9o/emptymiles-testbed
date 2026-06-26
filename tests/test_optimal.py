import pytest

from src.emptymiles_testbed.config import Config
from src.emptymiles_testbed.runner import evaluate
from src.emptymiles_testbed.strategies import Greedy, NoMatching

pytest.importorskip("ortools", reason="optimal matcher requires OR-Tools")
from src.emptymiles_testbed.strategies import Optimal  # noqa: E402


def _by_name(results):
    return {r.strategy: r for r in results}


def test_optimal_is_no_worse_than_greedy():
    """Under the same scenario, the optimal assignment should save at least as much CO₂
    as greedy (it can always reproduce greedy's choices)."""
    cfg = Config(seed=2, n_routes=15, n_orders=20)
    _, results = evaluate(cfg, [NoMatching(), Greedy(), Optimal()])
    m = _by_name(results)
    assert m["optimal"].co2_kg <= m["greedy"].co2_kg + 1e-6


def test_optimal_respects_capacity():
    cfg = Config(seed=2, n_routes=15, n_orders=20)
    scenario, results = evaluate(cfg, [Optimal()])
    assignments = {}
    # rebuild the assignment to check capacity feasibility
    a = Optimal().match(scenario, cfg)
    load = {}
    routes = {r.id: r for r in scenario.routes}
    orders = {o.id: o for o in scenario.orders}
    for oid, rid in a.items():
        if rid is not None:
            load[rid] = load.get(rid, 0.0) + orders[oid].weight_kg
    for rid, used in load.items():
        assert used <= routes[rid].capacity_kg + 1e-6
