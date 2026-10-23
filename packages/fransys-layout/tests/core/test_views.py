"""The core picks a symbol's view at the cell's orient and moves it; it turns nothing (SB4)."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from fransys_layout.core.errors import CoreError
from fransys_layout.core.geometry import cell_anchor, cell_footprint, pin_xy, view_of
from fransys_layout.core.pack_sep import hard_soft
from fransys_layout.core.place_assemble import _placed_cell
from fransys_layout.core.route_env import pin_sides
from fransys_layout.core.scene_facts import _pin_facts
from fransys_layout.core.sym_values import PinTurn, Sym, Turned
from fransys_layout.core.values import Box, Cell, Facts, Pin, PlacementProblem, Size

from .turn_fixtures import views_of

R90 = Turned(
    body=Box(3, 5, 40, 10),
    keepout=Box(1, 4, 50, 12),
    footprint=Box(-2, 3, 60, 14),
    pins=(PinTurn(33, 7, "W"), PinTurn(-4, 9, "E")),
    row_footprint=Box(-2, 3, 61, 15),
)
CELL = Cell("U", "R90", "a", "b")


def _planted() -> Sym:
    """A symbol whose R90 view is no turn of its R0 view: every R90 number is chosen apart."""
    pins = (Pin("a", "N", 0, -16, 0), Pin("b", "S", 0, 16, 1))
    box = Box(-8, -16, 16, 32)
    base = views_of(box, box, box, pins, ("R0",), row_footprint=box)
    return Sym(
        "U", None, "", Size(16, 8), pins, (("a",), ("b",)),
        views=frozendict({**base, "R90": R90})     )  # fmt: skip


def test_the_placed_cell_is_the_r90_view_moved_and_nothing_else() -> None:
    sym = _planted()
    env = SimpleNamespace(syms={"U": sym}, in_row=frozenset(), plan=SimpleNamespace(page=1))
    placed = _placed_cell(env, CELL, 100, 200)  # ty: ignore[invalid-argument-type] -- stand-in env
    assert placed.body == Box(103, 205, 40, 10)
    assert placed.footprint == Box(98, 203, 60, 14)
    assert [(p.pin, p.x, p.y) for p in placed.pin_xy] == [("a", 133, 207), ("b", 96, 209)]


def test_the_readers_pick_the_r90_view_not_a_turn_of_r0() -> None:
    sym = _planted()
    assert cell_footprint(sym, CELL, in_row=False) == R90.footprint
    assert cell_footprint(sym, CELL, in_row=True) == R90.row_footprint
    assert pin_xy(sym, CELL, "b") == (-4, 9)
    assert cell_anchor(sym, CELL) == (33, 7)
    assert hard_soft(sym, CELL, in_row=False, tag_stagger=True)[0] == Box(1, 4, 50, 12)


def test_a_missing_view_is_refused_naming_the_symbol() -> None:
    with pytest.raises(CoreError, match="symbol U has no view at R270"):
        view_of(replace(_planted()), "R270")


def test_the_pin_sides_are_the_views_not_a_turn_of_r0() -> None:
    problem = PlacementProblem(Size(100, 100), (_planted(),), (), facts=Facts())
    sides = pin_sides(problem)
    assert (sides["U", "a", "R0"], sides["U", "a", "R90"], sides["U", "b", "R90"]) == (
        "N",
        "W",
        "E",
    )
    fact = _pin_facts(problem.symbols[0], frozendict())["U", "a"]
    assert dict(fact.sides) == {"R0": "N", "R90": "W"}


def test_the_flat_geometry_of_a_sym_is_its_r0_view() -> None:
    """layout-0316: body, keepout, footprint and row_footprint read views["R0"], never a copy."""
    sym = _planted()
    r0 = sym.views["R0"]
    assert (sym.body, sym.keepout, sym.footprint, sym.row_footprint) == (
        r0.body,
        r0.keepout,
        r0.footprint,
        r0.row_footprint,
    )
    moved = replace(sym, views={"R0": replace(r0, body=Box(1, 2, 3, 4))})
    assert moved.body == Box(1, 2, 3, 4)
    with pytest.raises(CoreError):
        replace(sym, views={"R90": R90}).body  # noqa: B018 -- the property is the call
