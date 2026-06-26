"""The pluggable matcher interface - the heart of the testbed.

Implement one method and the whole harness (metrics, sweeps, dashboard) works with your
strategy for free. Drop your real matcher in here to benchmark it against the references.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..config import Config
from ..models import Scenario


class Strategy(ABC):
    name: str = "base"

    @abstractmethod
    def match(self, scenario: Scenario, cfg: Config) -> dict[int, int | None]:
        """Decide assignments.

        Returns a mapping {order_id: route_id} for matched orders, or {order_id: None}
        for orders left to a dedicated trip. Metrics are recomputed from this mapping
        alone, so a strategy never needs to report costs itself.
        """
        raise NotImplementedError
