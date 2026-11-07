"""The core builds the CONTENT-BOX bounds test measures, each solved once (invented demo data only).

w04 and p02 are the study instances, rebuilt from their named field tests (Ruling 43.2); the unit
outline, drawn-supply and pilot cases are small own copies of the P7.4 and P7.7 shapes.
"""

from dataclasses import replace
from functools import cache
from typing import TYPE_CHECKING

import fransys as fr
from _unit_outline_case import unit_outline_case_drafts
from conventions_fixtures import house
from fransys.colours import BU
from fransys_el import build, symbol_kit
from fransys_el.placement_options import options
from input_card_designs import field_case
from ring_cases import drawn_supply_model

from electrical_symbols import LIBRARY
from fransys_layout.core import Size, solve

if TYPE_CHECKING:
    from fransys_layout.core import CoreLayout, Options
    from fransys_model.kernel import Model

__all__ = ["CASES", "solved", "solved_in"]

W04 = "test_a_terminal_wired_to_devices_on_two_pages_is_drawn_on_each"
P02 = "test_a_strip_wired_outside_routes_every_wire_to_a_plc_module_under_it"


def _pilot() -> Model:
    """A coil K1 and a second coil K2 (the lamp) on one supply; K2 returns through K1's contact."""
    d = fr.design("demo_parts")
    supply = d.terminal_strip("X1", "DEMO-TB-2.5-TWIN", 2)
    k1, k2 = d.device("K1", "DEMO-RLY-2CO-24"), d.device("K2", "DEMO-RLY-2CO-24")
    with d.function("PILOT", "Pilot beside its coil"):
        d.series(supply[1], k1.coil, supply[2], wire=(BU, 0.75))
        d.series(supply[1], k2.coil, k1.co_1["11"], wire=(BU, 0.75))
        d.series(k1.co_1["14"], supply[2], wire=(BU, 0.75))
    return fr.build(d).model


CASES = {
    "w04": lambda: field_case(W04)._model(chained=True),
    "p02": lambda: field_case(P02)._built().model,
    "unit-outline": lambda: fr.build(*unit_outline_case_drafts()).model,
    "drawn-supply": drawn_supply_model,
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
    conventions = house()
    problem, _ = build(model, symbol_kit(model, LIBRARY), conventions, LIBRARY)
    return solve(replace(problem, area=area), options(conventions, LIBRARY))
