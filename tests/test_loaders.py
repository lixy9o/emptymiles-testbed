from src.emptymiles_testbed.config import Config
from src.emptymiles_testbed.generator import generate
from src.emptymiles_testbed.loaders import scenario_from_csv
from src.emptymiles_testbed.runner import evaluate

ROUTES_HEADER = "id,ox,oy,dx,dy,capacity_kg,emissions_g_per_km,cost_per_km,depart_time\n"
ORDERS_HEADER = "id,ox,oy,dx,dy,weight_kg,ready_time,due_time\n"


def _write_scenario_csvs(scenario, routes_path, orders_path):
    with open(routes_path, "w") as f:
        f.write(ROUTES_HEADER)
        for r in scenario.routes:
            f.write(f"{r.id},{r.origin[0]},{r.origin[1]},{r.dest[0]},{r.dest[1]},"
                    f"{r.capacity_kg},{r.emissions_g_per_km},{r.cost_per_km},{r.depart_time}\n")
    with open(orders_path, "w") as f:
        f.write(ORDERS_HEADER)
        for o in scenario.orders:
            f.write(f"{o.id},{o.origin[0]},{o.origin[1]},{o.dest[0]},{o.dest[1]},"
                    f"{o.weight_kg},{o.ready_time},{o.due_time}\n")


def test_roundtrip_csv_reproduces_results(tmp_path):
    """A generated scenario, written to CSV and replayed, yields identical metrics -
    proving the replay hook feeds the harness exactly like the generator does."""
    original = generate(Config(seed=5, n_routes=12, n_orders=18))
    rpath, opath = tmp_path / "routes.csv", tmp_path / "orders.csv"
    _write_scenario_csvs(original, rpath, opath)

    replayed = scenario_from_csv(str(rpath), str(opath))
    assert len(replayed.routes) == len(original.routes)
    assert len(replayed.orders) == len(original.orders)

    # run greedy on both via the same code path and compare CO₂
    from src.emptymiles_testbed.strategies import Greedy
    from src.emptymiles_testbed import metrics as m
    import time

    def co2(scn):
        t0 = time.perf_counter()
        a = Greedy().match(scn, Config(seed=5))
        return m.compute(scn, a, Config(seed=5), (time.perf_counter() - t0) * 1000, "greedy").co2_kg

    assert abs(co2(original) - co2(replayed)) < 1e-6
