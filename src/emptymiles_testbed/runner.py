"""Evaluate strategies on a scenario and report. `sweep_density` is the seed of module D
(network-liquidity analysis): vary order volume and watch match rate / CO₂ respond."""

from __future__ import annotations

import time

from . import metrics as metrics_mod
from .config import Config
from .generator import generate
from .metrics import Metrics
from .strategies import Greedy, NoMatching, Strategy

DEFAULT_STRATEGIES: list[Strategy] = [NoMatching(), Greedy()]


def evaluate(cfg: Config, strategies: list[Strategy] | None = None):
    """Run every strategy against the same generated scenario; return (scenario, [Metrics])."""
    strategies = strategies or DEFAULT_STRATEGIES
    scenario = generate(cfg)
    results = []
    for s in strategies:
        t0 = time.perf_counter()
        assignments = s.match(scenario, cfg)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        results.append(metrics_mod.compute(scenario, assignments, cfg, latency_ms, s.name))
    return scenario, results


def print_report(results: list[Metrics]) -> None:
    base = next((r for r in results if r.strategy == "none"), results[0])
    cols = (
        f"{'strategy':<10}{'match%':>8}{'total_km':>11}{'empty_km':>10}"
        f"{'CO2_kg':>9}{'cost':>9}{'CO2 vs base':>13}{'latency_ms':>12}"
    )
    print(cols)
    print("-" * len(cols))
    for r in results:
        saving = (1 - r.co2_kg / base.co2_kg) * 100 if base.co2_kg else 0.0
        print(
            f"{r.strategy:<10}{r.match_rate * 100:>7.1f}%{r.total_km:>11.1f}"
            f"{r.empty_km:>10.1f}{r.co2_kg:>9.1f}{r.cost:>9.1f}"
            f"{saving:>12.1f}%{r.latency_ms:>12.2f}"
        )


def sweep_density(cfg: Config, order_counts: list[int]) -> list[tuple[int, float, float]]:
    """Module-D seed: how do greedy's match rate and CO₂ move as order volume grows?"""
    rows = []
    for n in order_counts:
        _, results = evaluate(cfg.replace(n_orders=n))
        g = next(r for r in results if r.strategy == "greedy")
        rows.append((n, g.match_rate, g.co2_kg))
    return rows
