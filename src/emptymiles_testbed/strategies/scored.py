"""Scored greedy - assigns each order to the highest-scoring feasible route (Module C).

Same loop shape as `Greedy`, but the choice is driven by `Scorer` instead of raw detour, and
every committed match keeps its `MatchScore` (with reason codes) on `.explanations` so the
decision is inspectable after the fact.
"""

from __future__ import annotations

from ..config import Config
from ..models import Scenario
from ..scoring import MatchScore, Scorer
from .base import Strategy


class ScoredGreedy(Strategy):
    name = "scored"

    def __init__(self, scorer: Scorer | None = None):
        self._scorer = scorer
        self.explanations: dict[int, MatchScore] = {}

    def match(self, scenario: Scenario, cfg: Config) -> dict[int, int | None]:
        scorer = self._scorer or Scorer(cfg)
        assigned: dict[int, list] = {r.id: [] for r in scenario.routes}
        load: dict[int, float] = {r.id: 0.0 for r in scenario.routes}
        self.explanations = {}
        assignments: dict[int, int | None] = {}

        for order in sorted(scenario.orders, key=lambda o: o.ready_time):
            best: MatchScore | None = None
            for r in scenario.routes:
                s = scorer.score(r, assigned[r.id], load[r.id], order)
                if not s.feasible:
                    continue
                if best is None or s.score > best.score:
                    best = s

            if best is None:
                assignments[order.id] = None
            else:
                assignments[order.id] = best.route_id
                assigned[best.route_id].append(order)
                load[best.route_id] += order.weight_kg
                self.explanations[order.id] = best

        return assignments
