from src.emptymiles_testbed.config import Config
from src.emptymiles_testbed.forecasting import (
    EmptyLegForecaster,
    evaluate,
    make_world,
    net_spare_field,
    sample_day,
)


def _history(cfg, world, n=30):
    return [sample_day(world, cfg, day_seed=d) for d in range(1, n + 1)]


def test_field_conserves_mass():
    cfg = Config()
    world = make_world(cfg, world_seed=1)
    day = sample_day(world, cfg, day_seed=5)
    total = sum(net_spare_field(day, cfg).values())
    expected = sum(r.capacity_kg for r in day.routes) - sum(o.weight_kg for o in day.orders)
    assert abs(total - expected) < 1e-6


def test_world_is_stable_day_is_not():
    cfg = Config()
    world = make_world(cfg, world_seed=2)
    a = sample_day(world, cfg, day_seed=10)
    b = sample_day(world, cfg, day_seed=11)
    # different realisations...
    assert [o.origin for o in a.orders] != [o.origin for o in b.orders]
    # ...but same world structure underneath
    assert world.centers == make_world(cfg, world_seed=2).centers


def test_forecaster_beats_naive_baseline():
    cfg = Config()
    world = make_world(cfg, world_seed=7)
    fc = EmptyLegForecaster(cfg).fit(_history(cfg, world))
    ev = evaluate(fc, sample_day(world, cfg, day_seed=999), k=5)
    assert ev.rmse < ev.baseline_rmse  # learning the structure removes error
    assert ev.skill > 0.0


def test_precision_at_k_in_range():
    cfg = Config()
    world = make_world(cfg, world_seed=7)
    fc = EmptyLegForecaster(cfg).fit(_history(cfg, world))
    ev = evaluate(fc, sample_day(world, cfg, day_seed=999), k=5)
    assert 0.0 <= ev.precision_at_k <= 1.0


def test_forecast_is_deterministic():
    cfg = Config()
    world = make_world(cfg, world_seed=7)
    f1 = EmptyLegForecaster(cfg).fit(_history(cfg, world)).predict()
    f2 = EmptyLegForecaster(cfg).fit(_history(cfg, world)).predict()
    assert f1 == f2
