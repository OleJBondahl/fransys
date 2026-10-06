"""S20 M12 (ADDENDUM 19 fix 3): the terminals of one strip wired to each other stand in one row.

Terminals are the invented through symbol (`samples.drawn`) of kind `terminal`: port `10n + 1`
on top facing N, port `10n + 2` below facing S. A link joins two ports facing the same way.
"""

from dataclasses import replace

from samples import column, drawn, function_spec, hid

from fransys_layout.engines.schematic.defaults import kind_roles
from fransys_layout.stages import Connection, PortRef, Role
from fransys_layout.stages.terminal_rows import join_terminal_rows, terminal_chains


def _spec(number: int, *, strip: str = "X1"):
    return replace(
        function_spec(number, kind="terminal"), strip_text=strip, roles=kind_roles("terminal")
    )


def _drawn(number: int):
    return drawn(number, kind="terminal")


def _link(handle: int, a: tuple[int, int], b: tuple[int, int]) -> Connection:
    """Conductor `handle` between port `which` (1 top, 2 bottom) of two functions."""
    return Connection(
        handle=hid("conductor", handle),
        physical_net=hid("net", handle),
        role=Role.CONTROL,
        a=PortRef(function=hid("function", a[0]), port=hid("port", a[0] * 10 + a[1])),
        b=PortRef(function=hid("function", b[0]), port=hid("port", b[0] * 10 + b[1])),
    )


def _chains(numbers: tuple[int, ...], wires: tuple[Connection, ...], **strips: str):
    specs = tuple(_spec(n, strip=strips.get(f"s{n}", "X1")) for n in numbers)
    return terminal_chains(specs, tuple(_drawn(n) for n in numbers), wires).sets


def test_terminals_wired_on_one_side_are_one_chain() -> None:
    """1-2 and 2-3, top to top, are the chain {1, 2, 3}; terminal 4, unwired, is in none."""
    # UNDO: stages/terminal_rows.py `terminal_chains`: drop `joined.union(a.function, b.function)`
    wires = (_link(1, (1, 1), (2, 1)), _link(2, (2, 1), (3, 1)))
    assert _chains((1, 2, 3, 4), wires) == (tuple(hid("function", n) for n in (1, 2, 3)),)


def test_a_wire_from_a_top_port_to_a_bottom_port_is_no_link() -> None:
    """A cascade, inner of one to outer of the next, is not wired on one side."""
    # UNDO: stages/terminal_rows.py `terminal_chains`: drop the `facing.get(...) !=` test
    assert _chains((1, 2), (_link(1, (1, 1), (2, 2)),)) == ()


def test_terminals_of_two_strips_are_no_chain() -> None:
    """A jumper between strips is no strip's chain."""
    # UNDO: stages/terminal_rows.py `terminal_chains`: drop the `_strip(a) != _strip(b)` test
    assert _chains((1, 2), (_link(1, (1, 1), (2, 1)),), s2="X2") == ()


def _join(columns, numbers, wires, tie_key, *, fits=lambda _row: True):
    specs = tuple(_spec(n) for n in numbers)
    return join_terminal_rows(
        columns,
        specs,
        terminal_chains(specs, tuple(_drawn(n) for n in numbers), wires),
        tie_key=tie_key,
        fits=fits,
    )


def test_a_chain_stands_in_one_row_in_strip_order() -> None:
    """Three terminals in three columns become one column of one row, lanes in `tie_key` order."""
    # UNDO: stages/terminal_rows.py `join_terminal_rows`: sort `order` by `spec_of[f].key` alone
    columns = tuple(column(f"c{n}", (n,)) for n in (1, 2, 3))
    wires = (_link(1, (1, 1), (2, 1)), _link(2, (2, 1), (3, 1)))
    tie_key = {hid("function", 1): ("b",), hid("function", 2): ("c",), hid("function", 3): ("a",)}
    (row,) = _join(columns, (1, 2, 3), wires, tie_key)
    assert {cell.index for cell in row.cells} == {0}
    assert [(cell.function, cell.lane) for cell in row.cells] == [
        (hid("function", 3), 0),
        (hid("function", 1), 1),
        (hid("function", 2), 2),
    ]


def test_a_row_that_does_not_fit_stays_stacked() -> None:
    """Where `fits` refuses the row, the columns stay as they were."""
    # UNDO: stages/terminal_rows.py `join_terminal_rows`: drop `if not fits(built): continue`
    columns = tuple(column(f"c{n}", (n,)) for n in (1, 2))
    wires = (_link(1, (1, 1), (2, 1)),)
    assert _join(columns, (1, 2), wires, {}, fits=lambda _row: False) == columns


def test_a_chain_with_a_cell_of_another_function_in_its_column_stays_as_it_was() -> None:
    """The column of terminal 2 also holds function 9, which is no member: no row is made."""
    # UNDO: stages/terminal_rows.py `join_terminal_rows`: drop the `if any(not all(` check
    columns = (column("c1", (1,)), column("c2", (2, 9)))
    wires = (_link(1, (1, 1), (2, 1)),)
    assert _join(columns, (1, 2), wires, {}) == columns


def test_terminals_of_two_units_are_no_chain() -> None:
    """One strip tag in two units is two columns' worth, so no chain."""
    # UNDO: stages/terminal_rows.py `_strip`: drop `spec.unit` from the returned key
    specs = (_spec(1), replace(_spec(2), unit=hid("unit", 7)))
    wires = (_link(1, (1, 1), (2, 1)),)
    assert terminal_chains(specs, (_drawn(1), _drawn(2)), wires).sets == ()


def test_a_chain_with_a_member_that_stands_in_no_column_stays_as_it_was() -> None:
    """Terminal 2 has no cell: the row would hold a function no column placed."""
    # UNDO: stages/terminal_rows.py `join_terminal_rows`: drop the member-set (`sorted`) check
    columns = (column("c1", (1,)),)
    wires = (_link(1, (1, 1), (2, 1)),)
    assert _join(columns, (1, 2), wires, {}) == columns


def test_a_chain_with_a_replica_cell_stays_as_it_was() -> None:
    """A row rebuilt from bare cells would lose the replica flag."""
    # UNDO: stages/terminal_rows.py `_marked`: return False
    marked = column("c1", (1,))
    marked = replace(marked, cells=tuple(replace(c, replica=True) for c in marked.cells))
    columns = (marked, column("c2", (2,)))
    wires = (_link(1, (1, 1), (2, 1)),)
    assert _join(columns, (1, 2), wires, {}) == columns
