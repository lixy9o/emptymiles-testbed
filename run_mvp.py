#!/usr/bin/env python3
"""EmptyMiles Matching Testbed - MVP demo.

Compares the `none` baseline against `greedy` piggyback matching, then sweeps order
density to show how match rate and CO₂ respond to network liquidity (module-D preview).

    python run_mvp.py
"""

from src.emptymiles_testbed.config import Config
from src.emptymiles_testbed.runner import evaluate, print_report, sweep_density


def main() -> None:
    cfg = Config()
    print(
        f"EmptyMiles Matching Testbed - MVP   "
        f"(seed={cfg.seed}, routes={cfg.n_routes}, orders={cfg.n_orders})\n"
    )

    _, results = evaluate(cfg)
    print_report(results)

    print("\nDensity sweep (greedy) - match rate & CO₂ as order volume grows:")
    print(f"{'orders':>8}{'match%':>9}{'CO2_kg':>9}")
    for n, match_rate, co2 in sweep_density(cfg, [20, 40, 60, 80, 120, 160]):
        print(f"{n:>8}{match_rate * 100:>8.1f}%{co2:>9.1f}")


if __name__ == "__main__":
    main()
