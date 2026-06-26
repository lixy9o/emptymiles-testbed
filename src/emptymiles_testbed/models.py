"""Core domain objects. Plain dataclasses, no behaviour - kept deliberately small so
the matcher interface and metrics are the only places logic lives."""

from __future__ import annotations

from dataclasses import dataclass, field

Coord = tuple[float, float]  # (x, y) in km on the synthetic grid


@dataclass(frozen=True)
class Order:
    """A new delivery demand: move `weight_kg` from `origin` to `dest`, within a window."""

    id: int
    origin: Coord
    dest: Coord
    weight_kg: float
    ready_time: float  # minutes from sim start
    due_time: float


@dataclass
class PlannedRoute:
    """A trip a vehicle is making anyway (e.g. its own delivery run). Matching piggybacks
    new orders onto these to avoid dispatching separate vehicles - the Reload™ idea."""

    id: int
    origin: Coord
    dest: Coord
    capacity_kg: float
    emissions_g_per_km: float
    cost_per_km: float
    depart_time: float
    assigned_orders: list[int] = field(default_factory=list)


@dataclass
class Scenario:
    routes: list[PlannedRoute]
    orders: list[Order]
    seed: int
