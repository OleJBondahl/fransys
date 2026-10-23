"""Small own cases for the cross-link rows (extras beside the study rows), with their solve helper.

Invented demo data only (invariant 6). A coil stands for the lamp; the supply and the controller
are generic boxes the kit picks (P7.1 B).
"""

from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
from conventions_fixtures import house
from fransys.colours import BU
from fransys_el import build, options, symbol_kit

from electrical_symbols import LIBRARY
from fransys_layout.core import solve

if TYPE_CHECKING:
    from fransys_layout.core import CoreLayout
    from fransys_model.kernel import Model

__all__ = [
    "BANK",
    "NumberMovedError",
    "channels_model",
    "drawn_supply_model",
    "named",
    "pilot_model",
    "seal_in_model",
    "solved",
    "two_units_model",
]

BANK = 4


class NumberMovedError(Exception):
    """The measured number is not the one a strict xfail names: it is no AssertionError."""


def named(got: object, want: object, what: str) -> None:
    """Raise `NumberMovedError` unless `got` is `want`: an xfail then holds for that number only."""
    if got != want:
        msg = f"{what}: measured {got}, the xfail names {want}; re-measure and re-rule"
        raise NumberMovedError(msg)


def solved(model: Model) -> CoreLayout:
    """The core layout of `model` through `fransys_el.build`, the house kit and `solve`."""
    conventions = house()
    problem, _ = build(model, symbol_kit(model, LIBRARY), conventions, LIBRARY)
    return solve(problem, options(conventions, LIBRARY))


def seal_in_model() -> Model:
    """S2 in series with S1 parallel to K1's own contact, then the coil (nontree 1)."""
    d = fr.design("demo_parts")
    supply = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
    s1, s2 = d.device("S1", "DEMO-PB-NO"), d.device("S2", "DEMO-PB-NO")
    k1 = d.device("K1", "DEMO-RLY-2CO-24")
    with d.function("SEAL", "Seal-in"):
        d.series(supply[1], s2.sw, s1.sw, k1.coil, supply[2], wire=(BU, 0.75))
        d.detail.wire(s2.sw["B"], k1.co_1["11"], wire=(BU, 0.75))
        d.detail.wire(k1.co_1["14"], k1.coil["A1"], wire=(BU, 0.75))
    return fr.build(d).model


def pilot_model(*, crossed: bool = False) -> Model:
    """A coil K1 and a second coil K2 (the lamp) on one supply; K2 returns through K1's contact.

    `crossed` plants a third coil K3 from the lamp's far end back to the supply, which crosses.
    """
    d = fr.design("demo_parts")
    supply = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
    k1, k2 = d.device("K1", "DEMO-RLY-2CO-24"), d.device("K2", "DEMO-RLY-2CO-24")
    with d.function("PILOT", "Pilot beside its coil"):
        d.series(supply[1], k1.coil, supply[2], wire=(BU, 0.75))
        d.series(supply[1], k2.coil, k1.co_1["11"], wire=(BU, 0.75))
        d.series(k1.co_1["14"], supply[2], wire=(BU, 0.75))
        if crossed:
            k3 = d.device("K3", "DEMO-RLY-2CO-24")
            d.detail.wire(k2.coil["A2"], k3.coil["A1"], wire=(BU, 0.75))
            d.detail.wire(k3.coil["A2"], supply[1], wire=(BU, 0.75))
    return fr.build(d).model


class _Io(NamedTuple):
    x1: fr.TerminalStrip


@fr.unit("blk", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _block(d: Any) -> _Io:
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2, interface=True)
    load = d.device("K9", "DEMO-RLY-2CO-24")
    d.detail.wire(x1[1].inner, load.coil["A1"], wire=(BU, 0.75))
    d.detail.wire(x1[2].inner, load.coil["A2"], wire=(BU, 0.75))
    return _Io(x1)


def two_units_model() -> Model:
    """One contact K1 feeds the same load in units BLK0 and BLK1; the returns rejoin (nontree 4)."""
    d = fr.design("demo_parts")
    k1 = d.device("K1", "DEMO-RLY-2CO-24")
    u0, u1 = d.add(_block, "BLK0"), d.add(_block, "BLK1")
    with d.function("FEED", "Feed"):
        d.detail.wire(k1.co_1["14"], u0.x1[1].outer, wire=(BU, 0.75))
        d.detail.wire(k1.co_1["14"], u1.x1[1].outer, wire=(BU, 0.75))
        d.detail.wire(u0.x1[2].outer, u1.x1[2].outer, wire=(BU, 0.75))
    return fr.build(d).model


def drawn_supply_model() -> Model:
    """A supply box with + and - on one edge feeds a coil and a second coil; the loop closes (5)."""
    d = fr.design("demo_parts")
    with d.function("SUP", "Supply"):
        g1 = d.device("G1", None, pins=("P", "M"), external=True)
    k1, k2 = d.device("K1", "DEMO-RLY-2CO-24"), d.device("K2", "DEMO-RLY-2CO-24")
    with d.function("LOOP", "Supply loop"):
        d.detail.wire(g1["P"], k1.coil["A1"], wire=(BU, 0.75))
        d.detail.wire(g1["P"], k2.coil["A1"], wire=(BU, 0.75))
        d.detail.wire(k2.coil["A2"], k1.co_1["11"], wire=(BU, 0.75))
        d.detail.wire(k1.co_1["14"], g1["M"], wire=(BU, 0.75))
        d.detail.wire(k1.coil["A2"], g1["M"], wire=(BU, 0.75))
    return fr.build(d).model


def channels_model(count: int = 2) -> Model:
    """`count` coils, A1 on a feed terminal and A2 on an own channel of an external controller."""
    pins = tuple(f"CH{n:02d}-" for n in range(1, count + 1))
    d = fr.design("demo_parts")
    with d.function("PLC", "Controller"):
        plc = d.device("A1", None, pins=pins, external=True)
    live = d.terminal_strip("X1", "DEMO-TB-2.5", BANK)
    with d.function("B", "Relay bank"):
        for n in range(count):
            relay = d.device(f"K{n + 1}", "DEMO-RLY-2CO-24")
            d.detail.wire(live[1 + n % BANK], relay.coil["A1"], wire=(BU, 0.5))
            d.detail.wire(plc[pins[n]], relay.coil["A2"], wire=(BU, 0.5))
    return fr.build(d).model
