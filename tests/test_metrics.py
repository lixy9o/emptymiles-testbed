from src.emptymiles_testbed.config import Config
from src.emptymiles_testbed.runner import evaluate


def _by_name(results):
    return {r.strategy: r for r in results}


def test_greedy_never_worse_than_baseline():
    _, results = evaluate(Config(seed=1))
    m = _by_name(results)
    assert m["greedy"].co2_kg <= m["none"].co2_kg
    assert m["greedy"].empty_km <= m["none"].empty_km


def test_baseline_matches_nothing():
    _, results = evaluate(Config(seed=1))
    assert _by_name(results)["none"].matched == 0


def test_evaluation_is_reproducible():
    _, r1 = evaluate(Config(seed=7))
    _, r2 = evaluate(Config(seed=7))
    assert [x.co2_kg for x in r1] == [x.co2_kg for x in r2]


def test_some_matching_happens_in_clustered_world():
    # With clustering and a generous detour cap, greedy should match at least one order.
    _, results = evaluate(Config(seed=1, max_detour_km=15.0))
    assert _by_name(results)["greedy"].matched > 0
