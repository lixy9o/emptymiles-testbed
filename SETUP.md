# Setup & contributing

Clone-and-run in under a minute. The core needs **only the Python standard library**.

## Prerequisites

- **Python 3.10+** (uses `X | None` type syntax)
- `git`

## Quick start

```bash
git clone <repo-url> emptymiles-testbed
cd emptymiles-testbed
python run_mvp.py          # baseline vs greedy + a density sweep - no dependencies
```

## The demos

| Command | Shows |
|---|---|
| `python run_mvp.py` | Strategy scorecard (`none` vs `greedy`) + liquidity sweep |
| `python run_explain.py` | Module C - each match with plain-English reason codes |
| `python run_forecast.py` | Module B - empty-leg hotspot forecast + skill score |
| `streamlit run app.py` | Dashboard: map, scorecard, liquidity curve |

## Tests

```bash
pip install pytest
pytest                     # 25 passing; 1 skips unless OR-Tools is installed
```

## Optional dependencies (everything else runs without them)

```bash
pip install ortools                  # enables the `optimal` matcher (CP-SAT ceiling/oracle)
pip install streamlit matplotlib     # enables the dashboard (app.py)
```

Both are dependency-guarded: if they're absent, the rest of the project still runs and the
suite stays green (the OR-Tools test auto-skips).

## Add your own matching strategy

This is the main extension point. Implement one method:

```python
# src/emptymiles_testbed/strategies/mine.py
from ..config import Config
from ..models import Scenario
from .base import Strategy

class MyMatcher(Strategy):
    name = "mine"

    def match(self, scenario: Scenario, cfg: Config) -> dict[int, int | None]:
        # return {order_id: route_id} for matched orders, or {order_id: None} for dedicated
        ...
```

Then benchmark it against the references:

```python
from src.emptymiles_testbed.config import Config
from src.emptymiles_testbed.runner import evaluate, print_report
from src.emptymiles_testbed.strategies import NoMatching, Greedy
from src.emptymiles_testbed.strategies.mine import MyMatcher

_, results = evaluate(Config(), [NoMatching(), Greedy(), MyMatcher()])
print_report(results)
```

Metrics are recomputed purely from your returned mapping, so you can't accidentally score
yourself - every strategy is judged on the same accounting.

## Run real data through it

Provide two CSVs and the same harness evaluates them:

```python
from src.emptymiles_testbed.loaders import scenario_from_csv
scenario = scenario_from_csv("routes.csv", "orders.csv")
```

Expected headers:

```
routes: id, ox, oy, dx, dy, capacity_kg, emissions_g_per_km, cost_per_km, depart_time
orders: id, ox, oy, dx, dy, weight_kg, ready_time, due_time
```

## Conventions

- **Reproducibility:** everything is seeded via `Config`; same config → same numbers. Keep it
  that way (no unseeded randomness, no wall-clock in logic).
- **One source of truth for cost:** all distance/detour accounting lives in `geometry.py` and
  `metrics.py` - strategies decide *assignments*, never *costs*.
- **Emission factors** are illustrative (DEFRA/GLEC-grounded) in `emissions.py`; swap in the
  exact rows before quoting numbers externally.
- See `README.md` for the full module map and roadmap.
