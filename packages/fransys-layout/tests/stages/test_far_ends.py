"""`move_far_ends` (drawing conventions V5): hand-made values, no model and no engine.

Function 1 is the far pin (a column of its own in group 1); function 5 is a contact (or coil)
in a column of its own in group 2. Every symbol is the samples' vertical through symbol.
"""

from dataclasses import replace
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from samples import PROFILE, SHEET, column, drawn, hid

from fransys_layout.geometry import generic_box_geometry
from fransys_layout.geometry.symbols import channel_pitch
from fransys_layout.stages.far_ends import FarInputs, group_map, move_far_ends, sheet_fits
from fransys_layout.stages.types import Cell, Connection, Home, PortRef, Role

if TYPE_CHECKING:
    from fransys_layout.stages.types import Column, DrawnFunction, FunctionSpec


def _ref(number: int, end: str) -> PortRef:
    return PortRef(
        function=hid("function", number), port=hid("port", number * 10 + (end == "out") + 1)
    )


def _wire(number: int, a: PortRef, b: PortRef) -> Connection:
    return Connection(
        handle=hid("conductor", number),
        physical_net=hid("net", number),
        role=Role.CONTROL,
        a=a,
        b=b,
    )


def _moved(number: int, index: int, host: int, port: str) -> Cell:
    return Cell(
        function=hid("function", number),
        index=index,
        host=hid("function", host),
        port=port,
        home=Home.MOVED,
    )


def _cell(number: int, index: int) -> Cell:
    return Cell(function=hid("function", number), index=index)


def _run(
    drawn_functions: tuple[DrawnFunction, ...],
    wires: tuple[Connection, ...],
    columns: tuple[Column, ...],
    *,
    fits: bool = True,
) -> tuple[Column, ...]:
    far = FarInputs(drawn_functions, wires, {})
    return move_far_ends(columns, columns, far, lambda _column: fits)


def _pair(
    *, far: int = 1, near_group: int = 2, near: str = "contact_no", far_kind: str = "connector"
) -> tuple[tuple[DrawnFunction, ...], tuple[Column, ...]]:
    """Far pin 1 in group 1; function 5 of kind `near` in `near_group`."""
    columns = (column("pin", (far,)), column("far", (5,), group=near_group))
    return (drawn(far, kind=far_kind), drawn(5, kind=near)), columns


def test_a_contact_wired_to_a_pin_in_another_group_moves_its_home_there() -> None:
    """Contact 5 hangs on the `out` (S) pin of function 1: a home cell below it, own column gone."""
    # UNDO: stages/far_ends.py:_far_host, the group/drawing-set test `==` -> `!=` (inverted)
    # UNDO: stages/far_ends.py:_moved_cells, `home=Home.MOVED` -> `home=Home.HERE`
    drawn_functions, columns = _pair()
    wires = (_wire(1, _ref(1, "out"), _ref(5, "in")),)

    result = _run(drawn_functions, wires, columns)

    assert result == (replace(columns[0], cells=(_cell(1, 0), _moved(5, 1, 1, "out"))),)
    assert result[0].cells[1].home is Home.MOVED


def test_a_coil_wired_to_a_plc_output_channel_moves_like_a_contact() -> None:
    """Coil 5 on channel 1 moves below it; a coil on any other pin, and a plain terminal, stay."""
    # UNDO: stages/far_ends.py:_serves, the coil clause -> `mine.roles.coil`
    wires = (_wire(1, _ref(1, "out"), _ref(5, "in")),)
    drawn_functions, columns = _pair(near="coil", far_kind="plc_channel")
    stays_drawn, stays_columns = _pair(near="coil")
    terminal_drawn, terminal_columns = _pair(near="terminal", far_kind="plc_channel")

    assert _run(drawn_functions, wires, columns) == (
        replace(columns[0], cells=(_cell(1, 0), _moved(5, 1, 1, "out"))),
    )
    assert _run(stays_drawn, wires, stays_columns) == stays_columns
    assert _run(terminal_drawn, wires, terminal_columns) == terminal_columns


def test_sheet_fits_counts_the_rows_at_row_spacing_against_the_sheet_less_headroom() -> None:
    """Two rows of height 32 at spacing 104 need 168; the room is the height less four lanes."""
    # UNDO: stages/far_ends.py:_fits, `spacing * (len(heights) - 1)` -> `0`
    two = column("two", (1, 5))
    two = replace(two, cells=(_cell(1, 0), _cell(5, 1)))
    drawn_functions = (drawn(1), drawn(5))

    assert sheet_fits(drawn_functions, PROFILE, replace(SHEET, content_height=200), 4)(two)
    assert not sheet_fits(drawn_functions, PROFILE, replace(SHEET, content_height=199), 4)(two)


def test_a_contact_in_a_bundle_column_moves_alone_and_the_rest_closes_up() -> None:
    """Contact 5 shares its column with function 6: 5 moves to the pin, 6 stays at row 0."""
    # UNDO: stages/far_ends.py:move_far_ends, `for cell in column.cells:` -> only a one-cell column
    # UNDO: stages/far_ends.py:_compact, `rows[c.index]` -> `c.index` (the gap row stays)
    drawn_functions = (drawn(1, kind="connector"), drawn(5), drawn(6))
    columns = (column("pin", (1,)), column("bundle", (5, 6), group=2))
    wires = (_wire(1, _ref(1, "out"), _ref(5, "in")),)

    result = _run(drawn_functions, wires, columns)

    assert result == (
        replace(columns[0], cells=(_cell(1, 0), _moved(5, 1, 1, "out"))),
        replace(columns[1], cells=(_cell(6, 0),)),
    )


def test_a_coil_serves_a_flagged_channel_pin_of_a_box_that_is_no_all_channel_module() -> None:
    """A module with power pins is no `plc_channel` function: its channel ports carry the flag."""
    # UNDO: stages/far_ends.py:_is_channel, the `any(p.channel ...)` clause -> `False`
    wires = (_wire(1, _ref(1, "out"), _ref(5, "in")),)
    box = drawn(1, kind="connector")
    out = hid("port", 12)
    flagged = replace(box, ports=tuple(replace(p, channel=p.port == out) for p in box.ports))
    columns = (column("pin", (1,)), column("coil", (5,), group=2))

    moved = _run((flagged, drawn(5, kind="coil")), wires, columns)
    assert moved == (replace(columns[0], cells=(_cell(1, 0), _moved(5, 1, 1, "out"))),)
    assert _run((box, drawn(5, kind="coil")), wires, columns) == columns


def test_a_functions_group_is_its_hint_else_the_last_of_its_path() -> None:
    """layout-0103: the group V5 compares, by hint or the last node of the path, none when bare."""
    one, two, bare = (SimpleNamespace(function=hid("function", n)) for n in (1, 2, 3))
    one.group_hint, one.group_path = "hinted", ("a", "b")
    two.group_hint, two.group_path = None, ("a", "b")
    bare.group_hint, bare.group_path = None, ()
    groups = group_map(cast("tuple[FunctionSpec, ...]", (one, two, bare)))
    assert groups == {one.function: "hinted", two.function: "b", bare.function: None}


def test_a_box_whose_contacts_cannot_stand_a_channel_pitch_apart_on_a_page_does_not_fit() -> None:
    """layout-0103: 20 pins need 19 pitches and a contact; one G less and they stay home."""
    # UNDO: stages/far_ends.py:_fits, `and _span(drawn_of, column) <= width` -> ``
    names = tuple(f"p{n}" for n in range(20))
    box = replace(
        drawn(1), geometry=generic_box_geometry(names, ("s",) * 20), key=("invented", "box")
    )
    contact, last = drawn(5), drawn(6)
    cells = (_cell(1, 0), _moved(5, 1, 1, "p0"), _moved(6, 1, 1, "p19"))
    stacked = replace(
        column("box", (1, 5, 6)), cells=cells
    )  # contacts under the first and last pin
    need = 19 * channel_pitch() + contact.geometry.keepout.width
    wide = replace(SHEET, content_width=need)

    assert sheet_fits((box, contact, last), PROFILE, wide, 4)(stacked)
    narrow = replace(wide, content_width=need - 1)
    assert not sheet_fits((box, contact, last), PROFILE, narrow, 4)(stacked)


def _star(
    *, k2_group: int = 1
) -> tuple[tuple[DrawnFunction, ...], tuple[Connection, ...], tuple[Column, ...]]:
    """Terminal 1 under switch 2 in column `chain`, wired to coils 3 and 4 in columns of group 1.

    Coil 4's group is `k2_group`; function 2 shares the terminal's column, the coils are alone.
    """
    drawn_functions = (
        drawn(1, kind="terminal"),
        drawn(2),
        drawn(3, kind="coil"),
        drawn(4, kind="coil"),
    )
    wires = (
        _wire(1, _ref(2, "out"), _ref(1, "in")),
        _wire(2, _ref(1, "out"), _ref(3, "in")),
        _wire(3, _ref(1, "out"), _ref(4, "in")),
    )
    chain = replace(column("chain", (2, 1)), cells=(_cell(2, 0), _cell(1, 1)))
    columns = (chain, column("k1", (3,)), column("k2", (4,), group=k2_group))
    return drawn_functions, wires, columns


def test_a_terminal_wired_inside_its_own_group_stands_at_its_first_pin_outside_its_column() -> None:
    """Terminal 1 has a wire to 2 (own column) and to coils 3 and 4: it moves over 3, the first."""
    # UNDO: stages/own_group.py:_own_star, `min(outside, key=...)` -> `max(outside, key=...)`
    # UNDO: stages/own_group.py:own_group_homes, the `return` -> `return columns`
    drawn_functions, wires, columns = _star()

    result = _run(drawn_functions, wires, columns)

    assert result == (
        replace(columns[0], cells=(_cell(2, 0),)),
        replace(columns[1], cells=(_moved(1, 0, 3, "in"), _cell(3, 1))),
        columns[2],
    )
    assert result[1].cells[0].home is not Home.ELSEWHERE


def test_a_terminal_with_a_pin_in_another_group_stays_home() -> None:
    """Coil 4 stands in group 2: the terminal is no own-group star, so every column stays."""
    # UNDO: stages/own_group.py:_all_in_set, `all(...)` -> `any(...)`
    drawn_functions, wires, columns = _star(k2_group=2)

    assert _run(drawn_functions, wires, columns) == columns


def test_a_terminal_stays_home_when_the_host_column_does_not_fit() -> None:
    """`fits` says no: the star's columns stay as they were."""
    # UNDO: stages/own_group.py:own_group_homes, `or not fits(...)` -> ``
    drawn_functions, wires, columns = _star()

    assert _run(drawn_functions, wires, columns, fits=False) == columns
