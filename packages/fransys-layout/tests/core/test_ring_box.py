"""CORE-RING (layout-0327): a card box is one y node in stage 1, and a flipped fan swaps sides."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from fransys_layout.core import CoreError
from fransys_layout.core.pack import PlacedColumn
from fransys_layout.core.place_ring import ring_symbols
from fransys_layout.core.place_trunk import fan_roles
from fransys_layout.core.topology_split import y_cycles
from fransys_layout.core.values import Attach, Cell, Column, End, Fan, Lane, PinRef


def _cells(*names: str) -> tuple[Cell, ...]:
    return tuple(Cell(n, "R0", f"{n}.t", f"{n}.b") for n in names)


def _col(cid: str, *names: str, head: End, foot: End) -> Column:
    return Column(cid, (Lane(_cells(*names), 0),), (head,), (foot,), 0, 0)


def _box_end(box: str) -> End:
    return End("boxpin", pin=PinRef(box, "P"))


def _fan(fid: str, drivers: tuple[Attach, ...], legs: tuple[Attach, ...]) -> Fan:
    return Fan(fid, (fid,), drivers, legs, None, 1, "above")


def _at(col: str | None, cell: int, sym: str, pin: str) -> Attach:
    return Attach(col, 0, cell, PinRef(sym, pin))


FAN_END = End("fan")


def test_two_fans_closing_through_one_box_are_a_y_cycle() -> None:
    """The box is above the coil (its pin P drives it) and below it (the coil drives pin M)."""
    col = _col("cA", "a", head=FAN_END, foot=FAN_END)
    fans = (
        _fan("f1", (_at(None, 0, "G", "P"),), (_at("cA", 0, "a", "in"),)),
        _fan("f2", (_at("cA", 0, "a", "out"),), (_at(None, 0, "G", "M"),)),
    )
    assert y_cycles((col,), fans) != []


def test_one_fan_into_the_box_is_no_y_cycle() -> None:
    """Can fail the other way: a box pin on one side only is not a ring."""
    col = _col("cA", "a", head=FAN_END, foot=FAN_END)
    fans = (_fan("f1", (_at(None, 0, "G", "P"),), (_at("cA", 0, "a", "in"),)),)
    assert y_cycles((col,), fans) == []


def test_columns_standing_on_one_box_share_its_y_node() -> None:
    """Both heads stand on box G, level: A1 above B0 then closes a ring (A0 = B0 above A1)."""
    a = _col("cA", "a0", "a1", head=_box_end("G"), foot=FAN_END)
    b = _col("cB", "b0", "b1", head=_box_end("G"), foot=FAN_END)
    fan = _fan("f1", (_at("cA", 1, "a1", "x"),), (_at("cB", 0, "b0", "x"),))
    assert y_cycles((a, b), (fan,)) != []
    apart = _col("cB", "b0", "b1", head=FAN_END, foot=FAN_END)
    assert y_cycles((a, apart), (fan,)) == []


def _placed(cid: str, *, flipped: bool) -> PlacedColumn:
    return PlacedColumn(cid, ((),), (0,), 0, flipped=flipped)


def _env(**flipped: bool) -> Any:
    pcs = {cid: _placed(cid, flipped=f) for cid, f in flipped.items()}
    return SimpleNamespace(pcs=pcs)


def test_a_fan_wholly_in_flipped_columns_swaps_its_sides() -> None:
    fan = _fan("f", (_at("cA", 0, "a", "o"),), (_at("cB", 0, "b", "i"),))
    assert fan_roles(_env(cA=True, cB=True), fan) == (fan.legs, fan.drivers)


@pytest.mark.parametrize("flips", [{"cA": False, "cB": False}, {"cA": True, "cB": False}])
def test_a_fan_with_an_unflipped_column_keeps_its_sides(flips: dict[str, bool]) -> None:
    fan = _fan("f", (_at("cA", 0, "a", "o"),), (_at("cB", 0, "b", "i"),))
    assert fan_roles(_env(**flips), fan) == (fan.drivers, fan.legs)


def test_a_fan_on_a_box_pin_keeps_its_sides_in_flipped_columns() -> None:
    fan = _fan("f", (_at(None, 0, "G", "P"),), (_at("cB", 0, "b", "i"),))
    assert fan_roles(_env(cB=True), fan) == (fan.drivers, fan.legs)


def test_ring_symbols_names_cells_and_boxes_and_a_ycycleerror_is_a_core_error() -> None:
    from fransys_layout.core.constraints import Graph
    from fransys_layout.core.place_y import YCycleError

    g = Graph()
    g.after("cell:cA:0:0", "box:G", 8)
    g.after("box:G", "cell:cA:0:0", 8)
    g.after("row:0", "trunk:f:0", 8)
    pc = PlacedColumn("cA", (_cells("a"),), (0,), 0, flipped=False)
    env: Any = SimpleNamespace(pcs={"cA": pc})
    assert set(ring_symbols(env, g)) == {"G", "a"}
    assert issubclass(YCycleError, CoreError)
