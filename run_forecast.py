#!/usr/bin/env python3
"""Module-B demo: learn empty-leg hotspots from history, score against a held-out day.

    python run_forecast.py
"""

from src.emptymiles_testbed.config import Config
from src.emptymiles_testbed.forecasting import (
    N_BUCKETS,
    N_CELLS,
    EmptyLegForecaster,
    evaluate,
    make_world,
    sample_day,
)


def _cell_label(cell, cfg) -> str:
    cx, cy, tb = cell
    kx = (cx + 0.5) / N_CELLS * cfg.grid_size_km
    ky = (cy + 0.5) / N_CELLS * cfg.grid_size_km
    t0 = tb / N_BUCKETS * cfg.horizon_min
    t1 = (tb + 1) / N_BUCKETS * cfg.horizon_min
    return f"~({kx:.0f},{ky:.0f}) km, t={t0:.0f}-{t1:.0f} min"


def main() -> None:
    cfg = Config()
    world = make_world(cfg, world_seed=7)

    history = [sample_day(world, cfg, day_seed=d) for d in range(1, 31)]  # 30 days
    today = sample_day(world, cfg, day_seed=999)                          # held-out

    forecaster = EmptyLegForecaster(cfg).fit(history)
    ev = evaluate(forecaster, today, k=5)

    print(f"Empty-leg forecaster - trained on {len(history)} days, tested on a held-out day.\n")
    print(f"  forecast RMSE : {ev.rmse:8.1f} kg   (lower is better)")
    print(f"  baseline RMSE : {ev.baseline_rmse:8.1f} kg   (predict 'no imbalance')")
    print(f"  skill         : {ev.skill * 100:7.1f}%   of the baseline error removed")
    print(f"  precision@{ev.k}  : {ev.precision_at_k * 100:7.0f}%   of predicted hotspots were real\n")

    spare, deficit = forecaster.hotspots(k=5)
    print("Predicted EMPTY-LEG hotspots (spare capacity to fill):")
    for cell, val in spare:
        print(f"   +{val:7.0f} kg   {_cell_label(cell, cfg)}")
    print("\nPredicted DEFICIT hotspots (need capacity / dedicated trips likely):")
    for cell, val in deficit:
        print(f"   {val:8.0f} kg   {_cell_label(cell, cfg)}")


if __name__ == "__main__":
    main()
