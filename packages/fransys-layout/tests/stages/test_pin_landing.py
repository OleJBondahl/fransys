"""Columns stand in the order of the box pins they land on (R11, layout-0264): hand-made values."""

from dataclasses import replace

from samples import column, connection, drawn, hid

from fransys_layout.geometry import generic_box_geometry
from fransys_layout.stages import DrawnPort, Role
from fransys_layout.stages._packing import Unit
from fransys_layout.stages.pin_landing import (
    ColumnLanding,
    Side,
    column_landing,
    function_landing,
    in_pin_order,
    lanes_in_pin_order,
)
from fransys_layout.stages.types import Cell, Column, Connection, PortRef

BOX, OTHER = hid("function", 90), hid("function", 91)
SIDE: Side = (BOX, None)
OTHER_SIDE: Side = (OTHER, None)
NO_POWER = ({}, {}, {})


def _unit(name: str, *columns: str, role: Role = Role.CONTROL) -> Unit:
    keys = tuple(("invented", c) for c in columns)
    return Unit(
        groups=(hid("aspect_node", ord(name)),),
        columns=keys,
        width=10,
        break_before=False,
        role=role,
    )


def _land(rows: dict[str, dict[Side, int]]) -> ColumnLanding:
    return {("invented", name): ranks for name, ranks in rows.items()}


def _names(units) -> list[str]:
    return [c[1] for unit in units for c in unit.columns]


def test_units_landing_on_one_box_swap_into_the_order_of_its_pins() -> None:
    """Groups a, b, c hold one column each, landing on pins 3, 1, 2: they stand b, c, a."""
    # UNDO: stages/pin_landing.py:in_pin_order, return `list(units)` before the swaps
    units = [_unit("a", "a"), _unit("b", "b"), _unit("c", "c")]
    landing = _land({"a": {SIDE: 3}, "b": {SIDE: 1}, "c": {SIDE: 2}})
    assert _names(in_pin_order(units, landing)) == ["b", "c", "a"]


def test_a_unit_between_two_landing_units_keeps_its_place() -> None:
    """The group of column x lands nowhere: only the two landing groups trade places."""
    units = [_unit("a", "a"), _unit("x", "x"), _unit("b", "b")]
    landing = _land({"a": {SIDE: 2}, "b": {SIDE: 1}})
    assert _names(in_pin_order(units, landing)) == ["b", "x", "a"]


def test_units_of_two_roles_never_trade_places() -> None:
    # UNDO: stages/pin_landing.py:_slots, key the groups by `box` alone (the role dropped)
    units = [_unit("a", "a", role=Role.POWER), _unit("b", "b", role=Role.CONTROL)]
    landing = _land({"a": {SIDE: 2}, "b": {SIDE: 1}})
    assert _names(in_pin_order(units, landing)) == ["a", "b"]


def test_a_unit_landing_on_two_boxes_stays() -> None:
    # UNDO: stages/pin_landing.py:in_pin_order, drop the `len(boxes) == 1` test
    units = [_unit("a", "a"), _unit("b", "b")]
    landing = _land({"a": {SIDE: 2, OTHER_SIDE: 1}, "b": {SIDE: 1}})
    assert _names(in_pin_order(units, landing)) == ["a", "b"]


def test_columns_of_one_group_landing_on_a_box_stand_in_pin_order_around_the_others() -> None:
    units = [_unit("g", "a", "x", "b")]
    landing = _land({"a": {SIDE: 2}, "b": {SIDE: 1}})
    assert _names(in_pin_order(units, landing)) == ["b", "x", "a"]


def _bundle() -> Column:
    """One column of two rows of three strands: strand lane n holds functions 10 + n and 20 + n."""
    cells = tuple(
        Cell(function=hid("function", base + lane), index=row, lane=lane)
        for row, base in enumerate((10, 20))
        for lane in range(3)
    )
    return replace(column("bundle", ()), cells=cells)


def _lanes(result) -> list[list[int]]:
    return [[hid_n(c.function) for c in result.cells if c.index == row] for row in (0, 1)]


def hid_n(handle) -> int:
    return int(handle.value, 16)


def test_a_bundles_strands_turn_into_the_order_of_the_pins_they_land_on() -> None:
    """Strands 0, 1, 2 land on pins 3, 1, 2: the lanes become strand 1, 2, 0, in both rows."""
    # UNDO: stages/pin_landing.py:_turned, return `column` at once
    landing = {hid("function", 20 + n): {SIDE: rank} for n, rank in enumerate((3, 1, 2))}
    (turned,) = lanes_in_pin_order((_bundle(),), landing)
    by_lane = sorted(turned.cells, key=lambda c: (c.index, c.lane))
    assert [hid_n(c.function) for c in by_lane] == [11, 12, 10, 21, 22, 20]


def test_a_bundle_with_two_strands_on_one_pin_keeps_its_lanes() -> None:
    landing = {hid("function", 20 + n): {SIDE: rank} for n, rank in enumerate((1, 1, 2))}
    assert lanes_in_pin_order((_bundle(),), landing) == (_bundle(),)


def test_a_bundle_landing_on_two_boxes_keeps_its_lanes() -> None:
    landing = {
        hid("function", 20): {SIDE: 3},
        hid("function", 21): {SIDE: 1},
        hid("function", 22): {OTHER_SIDE: 2},
    }
    assert lanes_in_pin_order((_bundle(),), landing) == (_bundle(),)


def test_a_column_lands_on_the_lowest_pin_of_the_cells_it_draws_itself() -> None:
    hosted = Cell(function=hid("function", 3), index=1, host=hid("function", 1))
    base = column("a", (1, 2))
    both = replace(base, cells=(*base.cells, hosted))
    landing = {
        hid("function", 1): {SIDE: 5},
        hid("function", 2): {SIDE: 7},
        hid("function", 3): {SIDE: 1},
    }
    assert column_landing((both,), landing) == {both.key: {SIDE: 5}}


def _card(side_of: dict[str, str]):
    """Function 90 drawn as a generic box with pins `p`, `q` (model ports 901, 902), ranks 2, 1."""
    box = replace(drawn(90), geometry=generic_box_geometry(("p", "q"), tuple(side_of.values())))
    ports = (
        DrawnPort(port=hid("port", 901), symbol_port="p", order=2),
        DrawnPort(port=hid("port", 902), symbol_port="q", order=1),
    )
    return replace(box, ports=ports)


def _wire(number: int, function: int, port: int) -> Connection:
    return replace(
        connection(number, function, 90),
        a=PortRef(function=hid("function", function), port=hid("port", function * 10 + 1)),
        b=PortRef(function=BOX, port=hid("port", port)),
    )


def test_a_function_lands_on_a_pin_side_with_the_pins_marking_rank() -> None:
    """Function 1 is wired to pins p (rank 2) and q (rank 1), both free to turn: rank 1 wins."""
    # UNDO: stages/pin_landing.py:function_landing, `min(` -> `max(`
    found = function_landing(
        (drawn(1), _card({"p": "n", "q": "n"})), (_wire(1, 1, 901), _wire(2, 1, 902)), NO_POWER
    )
    assert found == {hid("function", 1): {(BOX, None): 1}}


def test_a_pin_whose_side_the_box_fixed_lands_on_that_side_apart_from_the_turning_pins() -> None:
    """Pin p is an item pin on the north side; q turns toward its partners: two sides of one box."""
    # UNDO: stages/pin_landing.py:function_landing, `side = None if ...` -> `side = None`
    card = _card({"p": "n", "q": "s"})
    wires = (_wire(1, 1, 901), _wire(2, 1, 902))
    power = ({}, {}, {hid("port", 901): "n"})
    north = next(g.facing.value for g in card.geometry.ports if g.name == "p")
    found = function_landing((drawn(1), card), wires, power)
    assert found == {hid("function", 1): {(BOX, north): 2, (BOX, None): 1}}
