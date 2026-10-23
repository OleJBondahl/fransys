"""A fan's leg on the node its drivers stand on leaves the fan alone; the rest keeps it (R418).

A card whose own supply pin hangs from the trunk while its inputs drive it holds a driver and a
leg on one y node. The cut takes out only that leg, as a cross link to a driver elsewhere; the
whole net leaving its fan (layout-0378) drew none of its other ends.
"""

from __future__ import annotations

from options_fixtures import core_options

from fransys_layout.core import PinRef
from fransys_layout.core.topology import ColumnEnv, _split_cycles
from fransys_layout.core.values import Attach, CrossLink, Fan

SUPPLY = Attach(None, 0, 0, PinRef("F", "out"), net="n")
INPUT = Attach(None, 0, 0, PinRef("CARD", "in.1"), net="n")
CARD_POWER = Attach(None, 0, 0, PinRef("CARD", "power"), net="n")
TERMINAL = Attach(None, 0, 0, PinRef("X", "1"), net="n")


def _split() -> tuple[tuple[Fan, ...], tuple[CrossLink, ...]]:
    fan = Fan("f:n", ("n",), (SUPPLY, INPUT), (CARD_POWER, TERMINAL), None, 1, "below")
    env = ColumnEnv(
        {},
        core_options(flip_turn="R180", driver_first=True, arrow_sides=("E", "W")),
        {"n": "f:n"},
        set(),
        {},
        {},
    )
    _, fans, cross = _split_cycles([], env, (fan,), ())
    return fans, cross


def test_the_conflicting_leg_leaves_and_the_rest_keeps_its_fan() -> None:
    fans, cross = _split()
    assert [(f.drivers, f.legs) for f in fans] == [((SUPPLY, INPUT), (TERMINAL,))]
    assert cross == (CrossLink("n", (CARD_POWER, SUPPLY)),)
