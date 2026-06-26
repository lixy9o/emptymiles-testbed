from src.emptymiles_testbed.config import Config
from src.emptymiles_testbed.models import Order, PlannedRoute
from src.emptymiles_testbed.runner import evaluate
from src.emptymiles_testbed.scoring import Scorer
from src.emptymiles_testbed.strategies import NoMatching, ScoredGreedy


def _route(**kw):
    base = dict(id=0, origin=(0.0, 0.0), dest=(10.0, 0.0), capacity_kg=1000.0,
               emissions_g_per_km=250.0, cost_per_km=1.2, depart_time=100.0)
    base.update(kw)
    return PlannedRoute(**base)


def _order(**kw):
    base = dict(id=0, origin=(3.0, 0.0), dest=(7.0, 0.0), weight_kg=100.0,
               ready_time=0.0, due_time=200.0)
    base.update(kw)
    return Order(**base)


def test_feasible_match_has_reasons():
    s = Scorer(Config()).score(_route(), [], 0.0, _order())
    assert s.feasible
    assert s.reasons and all(isinstance(r, str) for r in s.reasons)
    assert any("CO" in r for r in s.reasons)  # CO₂ reason present


def test_rejection_explains_capacity():
    s = Scorer(Config()).score(_route(capacity_kg=50.0), [], 0.0, _order(weight_kg=100.0))
    assert not s.feasible
    assert any("capacity" in r for r in s.reasons)


def test_rejection_explains_time_window():
    s = Scorer(Config()).score(_route(depart_time=500.0), [], 0.0, _order(due_time=200.0))
    assert not s.feasible
    assert any("time window" in r for r in s.reasons)


def test_carbon_losing_match_is_rejected():
    # a long detour for a tiny shipment ⇒ emits more than a dedicated trip ⇒ infeasible
    far_order = _order(origin=(0.0, 12.0), dest=(10.0, 12.0), weight_kg=10.0)
    s = Scorer(Config(max_detour_km=100.0)).score(_route(), [], 0.0, far_order)
    assert s.co2_saved_kg < 0
    assert not s.feasible
    assert any("emit more than a dedicated trip" in r for r in s.reasons)


def test_scored_strategy_never_loses_carbon_on_a_match():
    # every committed match must be carbon-positive after the guard
    cfg = Config(seed=42)
    matcher = ScoredGreedy()
    from src.emptymiles_testbed.generator import generate
    matcher.match(generate(cfg), cfg)
    assert matcher.explanations  # something matched
    assert all(e.co2_saved_kg >= 0 for e in matcher.explanations.values())


def test_on_line_order_saves_co2():
    # order sits on the route line ⇒ tiny detour ⇒ clear CO₂ saving
    s = Scorer(Config()).score(_route(), [], 0.0, _order())
    assert s.co2_saved_kg > 0


def test_scored_strategy_saves_vs_baseline_and_explains():
    cfg = Config(seed=1)
    matcher = ScoredGreedy()
    _, results = evaluate(cfg, [NoMatching(), matcher])
    by = {r.strategy: r for r in results}
    assert by["scored"].co2_kg <= by["none"].co2_kg
    # every matched order has an explanation with reason codes
    matched = [oid for oid, e in matcher.explanations.items()]
    assert matched
    for oid in matched:
        assert matcher.explanations[oid].reasons


def test_scored_is_deterministic():
    cfg = Config(seed=3)
    a = ScoredGreedy().match(__import__("src.emptymiles_testbed.generator", fromlist=["generate"]).generate(cfg), cfg)
    b = ScoredGreedy().match(__import__("src.emptymiles_testbed.generator", fromlist=["generate"]).generate(cfg), cfg)
    assert a == b
