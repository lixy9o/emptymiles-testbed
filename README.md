# EmptyMiles Matching Testbed

**Live demo:** https://emptymiles-testbed-h2e9azwsmykxwhbnvxcyne.streamlit.app

An **offline evaluation harness** for delivery-matching strategies. It generates a
synthetic-but-physically-honest logistics world (orders + planned routes), lets you
plug in any matching strategy behind a single interface, and reports the metrics that
actually matter: fill rate, empty-mile %, CO₂ vs. baseline, cost, and **compute latency**.

The point: you don't need production data to evaluate a matching algorithm. The
testbed *is* the data. When real order logs arrive, the same harness replays them
(see the `replay` hook on the roadmap).

## Why this design

```
 scenario generator ──▶ [ Matching Strategy ] ──▶ metrics
   (orders+routes)            ▲                   (fill rate, empty km,
   density / windows /        │                    CO₂ vs base, cost, latency)
   clustering / fleet    swap & A/B test
```

- **Pluggable matcher.** Every strategy implements one method: `match(scenario, cfg) -> {order_id: route_id | None}`. Drop your real matcher in and benchmark it against the references.
- **Reproducible.** Everything is seeded; same config → same numbers. The `optimal` strategy (roadmap) doubles as a correctness oracle on small instances.
- **Honest physics.** Volumes are synthetic; emission/cost factors are grounded in published DEFRA/GLEC figures (`emissions.py`). Replace with the exact DEFRA row before quoting any number externally.

## Project roadmap - A is the centerpiece, B/C/D plug in

| Module | What | Where it plugs in |
|---|---|---|
| **A - Testbed** (this repo) | Generator + matcher interface + metrics + sweeps | the platform |
| **B - Empty-leg forecasting** | Predict where/when empty legs appear | a `Forecaster` that feeds the generator / pre-positions capacity |
| **C - Match-quality scoring** | Interpretable score + reason codes per match | a `Scorer` the `Strategy` consumes (greedy already scores by detour - generalise it) |
| **D - Network-liquidity analysis** | Tipping points where matching "switches on" | the parameter-sweep harness (`runner.sweep_density`) is the seed of this |

## Run it

```bash
cd emptymiles-testbed
python run_mvp.py          # no dependencies needed for the MVP
pytest                     # run the tests
```

The MVP compares `none` (every order = a dedicated trip + empty return leg) against
`greedy` (piggyback each order onto the cheapest feasible existing route), then sweeps
order density to show how match rate and CO₂ move with network liquidity.

## Layout

```
run_mvp.py                     # entry point (stdlib only)
run_explain.py                 # Module-C demo: prints reason codes per match
run_forecast.py                # Module-B demo: empty-leg hotspot forecast + skill
app.py                         # Streamlit dashboard (needs streamlit + matplotlib)
conftest.py                    # puts repo root on sys.path for pytest
src/emptymiles_testbed/
  config.py                    # Config dataclass (seeded, JSON-loadable)
  emissions.py                 # DEFRA/GLEC-grounded reference factors
  geometry.py                  # distance + sequence-aware detour helpers
  models.py                    # Order, PlannedRoute, Scenario
  generator.py                 # synthetic scenario generator
  loaders.py                   # scenario_from_csv() - the real-data replay hook
  scoring.py                   # Module C: Scorer + MatchScore (reason codes)
  forecasting.py               # Module B: World + EmptyLegForecaster + skill eval
  metrics.py                   # metrics (single source of truth)
  runner.py                    # evaluate(), print_report(), sweep_density()
  strategies/
    base.py                    # Strategy ABC  ← the pluggable interface
    none_strategy.py           # baseline
    greedy.py                  # nearest-feasible piggyback (sequence-aware)
    scored.py                  # Module C: picks the highest-scoring match
    optimal.py                 # OR-Tools CP-SAT ceiling / oracle
tests/
```

## Roadmap

1. **MVP (done):** grid world, `none` vs `greedy`, core metrics, density sweep.
2. **Credible (done):**
   - **Sequence-aware detour** - orders compound on a route (`geometry.sequence_detour`), not costed in isolation.
   - **`optimal` matcher** (`strategies/optimal.py`, OR-Tools CP-SAT) - a CO₂ ceiling + correctness oracle. `pip install ortools`.
   - **Replay hook** (`loaders.scenario_from_csv`) - run real order/route logs through the same harness.
   - Real road-network distances remain a hook (`geometry.road_distance`) until the dependency is worth it.
3. **Pitch-ready:**
   - **Dashboard (done):** `streamlit run app.py` - scenario map, scorecard, liquidity curve. `pip install streamlit matplotlib`.
   - **Module C - match scoring (done):** `scoring.Scorer` turns each candidate into a `MatchScore` (CO₂ saved, detour, capacity fit, time slack) with plain-English reason codes - and reasons for *rejections*, including a carbon guard (no match that emits more than a dedicated trip). Used by `strategies/scored.py`; see it explain itself with `python run_explain.py`.
   - **Module B - empty-leg forecasting (done):** `forecasting.py` models a stable `World` (fixed demand/supply hotspots), samples day-to-day realisations, and learns the expected spare-capacity field. Scored with RMSE skill + precision@k against a held-out day. Run `python run_forecast.py`.

## Background and credits

The problem this explores - cutting empty running miles by matching deliveries to spare
vehicle capacity - was inspired by the UK same-day / last-mile logistics-technology space.
This is an independent project built entirely on synthetic data; it is not affiliated with,
endorsed by, or built using any company's data or systems.

Built with help from [Claude Code](https://claude.com/claude-code) (Anthropic).
