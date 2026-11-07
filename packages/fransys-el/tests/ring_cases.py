"""The stage-1 y-cycle instances of CORE-RING (layout-0327) as models, with their solve helper.

Invented demo data only (invariant 6). Where `symbol_kit` has no pick yet (a supply or a
controller box: KIT-FACTS), `box_kit` draws the function as a generic box on its port names.
"""

from dataclasses import replace
from typing import TYPE_CHECKING, Any

import fransys as fr
from _bank_case import built_bank
from conventions_fixtures import house
from fransys.colours import BU
from fransys_el import build, symbol_kit
from fransys_el.placement_kit import Pick
from fransys_el.placement_options import options

from electrical_symbols import LIBRARY
from fransys_layout.core import solve
from fransys_model.vocab import functions, ports

if TYPE_CHECKING:
    from fransys_layout.core import CoreLayout
    from fransys_model.kernel import Model

__all__ = ["bank_model", "box_kit", "built_bank", "channels_model", "drawn_supply_model", "score_of", "solved"]

BANK = 4


def box_kit(model: Model) -> Any:
    """`symbol_kit`, and for a function it has no pick for, a generic box on its port names."""
    kit = dict(symbol_kit(model, LIBRARY))
    named = ports(model)
    for function in functions(model):
        if function not in kit:
            names = {p: r.name for p, r in named.items() if r.function == function}
            kit[function] = Pick("generic-box", 1, frozendict(names))
    return frozendict(kit)


def score_of(layout: CoreLayout) -> Any:
    """The layout's score, which `solve` always sets."""
    assert layout.score is not None
    return layout.score


def solved(model: Model, *, generic: bool = False, **changes: Any) -> CoreLayout:
    """The core layout of `model`; `generic` also boxes the functions the kit has no pick for."""
    conventions = house()
    kit = box_kit(model) if generic else symbol_kit(model, LIBRARY)
    problem, _ = build(model, kit, conventions, LIBRARY)
    opts = options(conventions, LIBRARY)
    return solve(problem, replace(opts, **changes))


def drawn_supply_model() -> Model:
    """A supply box with + and - on one edge feeds a coil and a second coil; the loop closes."""
    d = fr.design("demo_parts")
    with d.function("SUP", "Supply"):
        g1 = d.device("G1", None, pins=("P", "M"), external=True)
    k1, k2 = d.device("K1", "DEMO-RLY-2CO-24"), d.device("K2", "DEMO-RLY-2CO-24")
    with d.function("LOOP", "Supply loop"):
        d.series(g1["P"], k1.coil["A1"], wire=(BU, 0.75))
        d.series(g1["P"], k2.coil["A1"], wire=(BU, 0.75))
        d.series(k2.coil["A2"], k1.co_1["11"], wire=(BU, 0.75))
        d.series(k1.co_1["14"], g1["M"], wire=(BU, 0.75))
        d.series(k1.coil["A2"], g1["M"], wire=(BU, 0.75))
    return fr.build(d).model


def channels_model(count: int = 2) -> Model:
    """`count` coils, A1 on a feed terminal and A2 on an own channel of an external controller."""
    pins = tuple(f"CH{n:02d}-" for n in range(1, count + 1))
    d = fr.design("demo_parts")
    with d.function("PLC", "Controller"):
        plc = d.device("A1", None, pins=pins, external=True)
    live = d.terminal_strip("X1", "DEMO-TB-2.5-TWIN", BANK)
    with d.function("B", "Relay bank"):
        relays = []
        for n in range(count):
            relay = d.device(f"K{n + 1}", "DEMO-RLY-2CO-24")
            relays.append(relay)
            feed = live[1 + n % BANK].inner if n < 2 * BANK else relays[n - BANK].coil["A1"]  # a point takes 2 (R1266): the rest chain pin to pin
            d.series(feed, relay.coil["A1"], wire=(BU, 0.5))
            d.series(plc[pins[n]], relay.coil["A2"], wire=(BU, 0.5))
    return fr.build(d).model


def bank_model(count: int = 16) -> Model:
    """`count` relays, each in its own function, on one controller, with lamps (the w08 shape)."""
    return built_bank(count).model
