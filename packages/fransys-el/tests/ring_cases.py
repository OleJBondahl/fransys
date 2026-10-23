"""The stage-1 y-cycle instances of CORE-RING (layout-0327) as models, with their solve helper.

Invented demo data only (invariant 6). Where `symbol_kit` has no pick yet (a supply or a
controller box: KIT-FACTS), `box_kit` draws the function as a generic box on its port names.
"""

import tempfile
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
from conventions_fixtures import house
from fransys.colours import BU
from fransys_el import Pick, build, options, symbol_kit

from electrical_symbols import LIBRARY
from fransys_layout.core import solve
from fransys_model.vocab import functions, ports

if TYPE_CHECKING:
    from fransys_layout.core import CoreLayout
    from fransys_model.kernel import Model

__all__ = ["bank_model", "box_kit", "channels_model", "drawn_supply_model", "solved"]

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


class _Io(NamedTuple):
    feed: fr.TerminalStrip


_PINS = tuple(f"CH{j:02d}-" for j in range(1, 17))
_SHEET = {
    "width_mm": 420,
    "height_mm": 297,
    "content_x_mm": 10,
    "content_y_mm": 10,
    "content_width_mm": 400,
    "content_height_mm": 277,
    "frame_columns": 8,
    "frame_rows": 6,
}


def bank_model(count: int = 16) -> Model:
    """`count` relays, each in its own function, on one controller, with lamps (the w08 shape)."""

    @fr.unit("demo-bank", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
    def bank(u: fr.Design) -> _Io:
        sheet = u.layout.sheet("S3", **_SHEET, module_mm=Decimal("3.0"))
        u.layout.profile(sheet=sheet)
        feed = u.terminal_strip("X1", "DEMO-TB-2.5", 8, interface=True)
        back = u.terminal_strip("X2", "DEMO-TB-2.5", 8)
        with u.function("PLC", "Controller"):
            controller = u.device("A1", None, pins=_PINS, external=True)
        for i in range(count):
            with u.function(f"R{i + 1}", f"Relay {i + 1}"):
                relay = u.device(f"K{i + 1}", "DEMO-RLY-2CO-24")
                u.detail.wire(feed[1 + i % 4], relay.coil["A1"], wire=("WH", 0.75))
                u.detail.wire(controller[_PINS[i % 16]], relay.coil["A2"], wire=("BU", 0.75))
                lamp = u.device(f"P{i + 1}", "DEMO-LAMP-24")
                u.detail.wire(relay.co_1["14"], lamp.lamp[1], wire=("WH", 0.75))
                u.detail.wire(back[1 + i % 6], relay.co_1["11"], wire=("WH", 0.75))
                u.detail.wire(lamp.lamp[2], back[7], wire=("BU", 0.75))
        return _Io(feed)

    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Bank\n", encoding="utf-8")
        d = fr.design("demo_parts")
        d.add(bank, "U1")
        document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-bank", cover=cover)
        return fr.build(d, document).model
