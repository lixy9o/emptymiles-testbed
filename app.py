"""Streamlit dashboard for the EmptyMiles Matching Testbed.

Run:  pip install streamlit matplotlib  &&  streamlit run app.py

Shows three things non-engineers can read at a glance:
  1. the scenario map (planned routes + order pickups),
  2. the strategy scorecard (none vs greedy [vs optimal, if OR-Tools is installed]),
  3. the liquidity curve (match rate & CO₂ as order volume grows - module D).
"""

from __future__ import annotations

import sys

try:
    import matplotlib.pyplot as plt
    import streamlit as st
except ImportError:  # pragma: no cover
    sys.exit("This dashboard needs: pip install streamlit matplotlib")

from src.emptymiles_testbed.config import Config
from src.emptymiles_testbed.generator import generate
from src.emptymiles_testbed.runner import evaluate, sweep_density
from src.emptymiles_testbed.strategies import Greedy, NoMatching

try:
    from src.emptymiles_testbed.strategies import Optimal
    from src.emptymiles_testbed.strategies.optimal import cp_model

    HAS_ORTOOLS = cp_model is not None
except Exception:  # pragma: no cover
    HAS_ORTOOLS = False

st.set_page_config(page_title="EmptyMiles Matching Testbed", layout="wide")
st.title("EmptyMiles Matching Testbed")
st.caption("A flight simulator for the matcher - swap strategies, read off fuel burned.")

# --- sidebar: the scenario knobs ---
st.sidebar.header("Scenario")
cfg = Config(
    seed=st.sidebar.number_input("seed", value=42, step=1),
    n_routes=st.sidebar.slider("planned routes", 5, 120, 40),
    n_orders=st.sidebar.slider("orders", 5, 200, 60),
    cluster_prob=st.sidebar.slider("clustering", 0.0, 1.0, 0.6),
    max_detour_km=st.sidebar.slider("max detour (km)", 1.0, 25.0, 8.0),
)

strategies = [NoMatching(), Greedy()]
if HAS_ORTOOLS and st.sidebar.checkbox("include optimal (OR-Tools)", value=False):
    strategies.append(Optimal())

scenario, results = evaluate(cfg, strategies)
base = next(r for r in results if r.strategy == "none")

left, right = st.columns(2)

with left:
    st.subheader("Scenario map")
    fig, ax = plt.subplots()
    for r in scenario.routes:
        ax.plot([r.origin[0], r.dest[0]], [r.origin[1], r.dest[1]], color="#bbb", lw=0.6, zorder=1)
    ax.scatter([o.origin[0] for o in scenario.orders],
               [o.origin[1] for o in scenario.orders],
               s=12, color="#1f77b4", zorder=2, label="order pickups")
    ax.set_xlabel("km"); ax.set_ylabel("km"); ax.legend(loc="upper right")
    st.pyplot(fig)

with right:
    st.subheader("Scorecard")
    st.table(
        [
            {
                "strategy": r.strategy,
                "match %": f"{r.match_rate * 100:.1f}",
                "empty km": f"{r.empty_km:.0f}",
                "CO₂ kg": f"{r.co2_kg:.1f}",
                "CO₂ vs base": f"{(1 - r.co2_kg / base.co2_kg) * 100:.1f}%" if base.co2_kg else "-",
                "latency ms": f"{r.latency_ms:.2f}",
            }
            for r in results
        ]
    )

st.subheader("Liquidity curve - match rate & CO₂ vs order volume (module D)")
rows = sweep_density(cfg, [20, 40, 60, 80, 120, 160])
fig2, ax1 = plt.subplots()
ns = [n for n, _, _ in rows]
ax1.plot(ns, [m * 100 for _, m, _ in rows], "o-", color="#1f77b4")
ax1.set_xlabel("orders"); ax1.set_ylabel("greedy match %", color="#1f77b4")
ax2 = ax1.twinx()
ax2.plot(ns, [c for _, _, c in rows], "s--", color="#d62728")
ax2.set_ylabel("greedy CO₂ (kg)", color="#d62728")
st.pyplot(fig2)
