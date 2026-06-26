"""Baseline: no matching. Every order becomes its own dedicated trip (+ empty return leg).
This is the counterfactual every CO₂-saving claim is measured against."""

from __future__ import annotations

from ..config import Config
from ..models import Scenario
from .base import Strategy


class NoMatching(Strategy):
    name = "none"

    def match(self, scenario: Scenario, cfg: Config) -> dict[int, int | None]:
        return {o.id: None for o in scenario.orders}
