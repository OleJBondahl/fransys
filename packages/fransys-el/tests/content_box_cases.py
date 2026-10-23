"""The core builds the CONTENT-BOX bounds test measures, each solved once (invented demo data only).

w04 and p02 are the study instances, rebuilt from their named field tests (Ruling 43.2); the unit
outline, drawn-supply and pilot cases are small own copies of the P7.4 and P7.7 shapes.
"""

import importlib.util
import sys
import tempfile
from dataclasses import replace
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
from conventions_fixtures import house
from fransys.colours import BU
from fransys_el import build, options, symbol_kit

from electrical_symbols import LIBRARY
from fransys_layout.core import Size, solve

if TYPE_CHECKING:
    from fransys_layout.core import CoreLayout, Options
    from fransys_model.kernel import Model

__all__ = ["CASES", "solved", "solved_in"]

ROOT = Path(__file__).resolve().parents[3]
W04 = "test_a_terminal_wired_to_devices_on_two_pages_is_drawn_on_each"
P02 = "test_a_strip_wired_outside_routes_every_wire_to_a_plc_module_under_it"
TERMINALS = 4


def _field_case(name: str) -> Any:
    """A field-case module, loaded by path (a `test_` module cannot be imported)."""
    sys.path.insert(0, str(ROOT / "tests"))
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "tests" / "field_cases" / f"{name}.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Io(NamedTuple):
    X: Any


@fr.unit("demo-switch-cab", revision=1, interface_version=1, date="2026-01-01", text="1", by="AB")
def _cab(u: Any) -> _Io:
    x = u.terminal_strip("X", "DEMO-TB-2.5", TERMINALS, interface=True)
    for n in range(1, TERMINALS + 1):
        button = u.device(f"S{n}", "DEMO-PB-NO")
        u.detail.wire(x[n], button.sw["A"], wire=(BU, 0.5))
    return _Io(x)


def _unit_outline() -> Model:
    """Unit U1 (interface strip X, four push buttons) and a field strip X9, every net crossing."""
    d = fr.design("demo_parts")
    room = d.location("R", "Room")
    cab = d.add(_cab, "U1", place="R")
    field = d.terminal_strip("X9", "DEMO-TB-2.5", TERMINALS, external=True, place="R")
    for n in range(1, TERMINALS + 1):
        d.detail.wire(cab.X[n], field[n], wire=(BU, 0.5))
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Room\n", encoding="utf-8")
        return fr.build(
            d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, room, cover=cover)
        ).model


def _drawn_supply() -> Model:
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


def _pilot() -> Model:
    """A coil K1 and a second coil K2 (the lamp) on one supply; K2 returns through K1's contact."""
    d = fr.design("demo_parts")
    supply = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
    k1, k2 = d.device("K1", "DEMO-RLY-2CO-24"), d.device("K2", "DEMO-RLY-2CO-24")
    with d.function("PILOT", "Pilot beside its coil"):
        d.series(supply[1], k1.coil, supply[2], wire=(BU, 0.75))
        d.series(supply[1], k2.coil, k1.co_1["11"], wire=(BU, 0.75))
        d.series(k1.co_1["14"], supply[2], wire=(BU, 0.75))
    return fr.build(d).model


CASES = {
    "w04": lambda: _field_case(W04)._model(chained=True),
    "p02": lambda: _field_case(P02)._built().model,
    "unit-outline": _unit_outline,
    "drawn-supply": _drawn_supply,
    "pilot": _pilot,
}


@cache
def solved(name: str) -> tuple[CoreLayout, Options]:
    """The core layout of case `name` and the options it was solved with."""
    model = CASES[name]()
    conventions = house()
    problem, _ = build(model, symbol_kit(model, LIBRARY), conventions, LIBRARY)
    chosen = options(conventions, LIBRARY)
    return solve(problem, chosen), chosen


def solved_in(name: str, area: Size) -> CoreLayout:
    """Case `name` solved on a page of `area` instead of the house page."""
    model = CASES[name]()
    conventions = replace(house(), area=area)
    problem, _ = build(model, symbol_kit(model, LIBRARY), conventions, LIBRARY)
    return solve(problem, options(conventions, LIBRARY))
