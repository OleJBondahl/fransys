"""A fan's own attachment footprint does not move its trunk (R523, R515)."""

from __future__ import annotations

from turn_fixtures import refit

from fransys_layout.core import Box

from .flow_builders import elem, net, problem
from .pipeline_fixtures import placed_of


def _trunk_y(driver_foot: Box | None, leg_foot: Box | None) -> int:
    d, k, m = elem("d", 16), elem("k", 16), elem("m", 16)
    if driver_foot:
        d = refit(d, footprint=driver_foot)
    if leg_foot:
        k, m = refit(k, footprint=leg_foot), refit(m, footprint=leg_foot)
    (trunk,) = placed_of(problem([d, k, m], [net("x", "d.s", "k.n", "m.n")])).pages[0].trunks
    return trunk.y


def test_a_fan_own_driver_footprint_never_moves_its_trunk() -> None:
    """R523: the driver's footprint reaches 56 below its pin; the trunk stays put."""
    assert _trunk_y(Box(-8, -16, 16, 72), None) == _trunk_y(None, None)
