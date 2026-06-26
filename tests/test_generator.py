from src.emptymiles_testbed.config import Config
from src.emptymiles_testbed.generator import generate


def test_seed_is_deterministic():
    a = generate(Config(seed=3))
    b = generate(Config(seed=3))
    assert [o.origin for o in a.orders] == [o.origin for o in b.orders]
    assert [r.dest for r in a.routes] == [r.dest for r in b.routes]


def test_counts_match_config():
    s = generate(Config(n_routes=10, n_orders=15))
    assert len(s.routes) == 10
    assert len(s.orders) == 15


def test_points_stay_on_grid():
    cfg = Config(seed=11)
    s = generate(cfg)
    for o in s.orders:
        for x in (*o.origin, *o.dest):
            assert 0.0 <= x <= cfg.grid_size_km
