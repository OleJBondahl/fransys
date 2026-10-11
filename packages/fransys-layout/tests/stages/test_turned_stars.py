"""A conductor that would turn back round a device is a reference pair.

Function `n` is the through symbol (`samples.drawn`): port `10n + 1` at the top, facing N; port
`10n + 2` below, facing S. Columns stand left to right on page 1, stacked by `place`'s own rule.
"""

from dataclasses import replace

from samples import PROFILE, SHEET, column, drawn, function_spec, hid, page_plan

from fransys_layout.engines.schematic.defaults import kind_roles
from fransys_layout.stages import Connection, PortRef, Role
from fransys_layout.stages.page_stacking import PageStacking
from fransys_layout.stages.place import page_stack
from fransys_layout.stages.references.turned import turned_stars
from fransys_layout.stages.references.types import Seating
from fransys_layout.stages.terminal_rows import terminal_chains
from fransys_layout.stages.types import PlannedColumn


def _wire(handle: int, a: tuple[int, int], b: tuple[int, int]) -> Connection:
    """Conductor `handle` between ports `a` and `b`, each `(function, which)`: 1 top, 2 bottom."""
    return Connection(
        handle=hid("conductor", handle),
        physical_net=hid("net", handle),
        role=Role.CONTROL,
        a=PortRef(function=hid("function", a[0]), port=hid("port", a[0] * 10 + a[1])),
        b=PortRef(function=hid("function", b[0]), port=hid("port", b[0] * 10 + b[1])),
    )


def _spec(number: int, *, terminal: bool):
    if not terminal:
        return function_spec(number)
    return replace(
        function_spec(number, kind="terminal"), strip_text="X1", roles=kind_roles("terminal")
    )


def _turned(
    wires: tuple[Connection, ...],
    *columns: tuple[str, tuple[int, ...]],
    off_ports: frozenset = frozenset(),
    terminals: frozenset[int] = frozenset(),
):
    """The stars of `wires` on `columns` (each `(name, functions top to bottom)`).

    The functions of `terminals` are terminals of one strip, X1.
    """
    built = tuple(
        replace(column(name, numbers), key=("invented", name)) for name, numbers in columns
    )
    plan = replace(
        page_plan(tuple(name for name, _ in columns)),
        columns=tuple(PlannedColumn(column=one.key, index=i) for i, one in enumerate(built)),
    )
    numbers = sorted({n for _, one in columns for n in one})
    kind = dict.fromkeys(terminals, "terminal")
    functions = tuple(drawn(n, kind=kind.get(n, "contact_no")) for n in numbers)
    stack = page_stack(plan, built, functions, PageStacking(profile=PROFILE, sheet=SHEET))
    specs = tuple(_spec(n, terminal=n in terminals) for n in numbers)
    return turned_stars(
        wires,
        specs,
        Seating((plan,), built, functions, (), {(1, 1): stack}),
        chains=terminal_chains(specs, functions, wires),
        off_ports=off_ports,
    )


def test_a_bottom_pin_wired_to_a_pin_above_it_is_a_reference_pair() -> None:
    """Port 12 (S) of function 1, in row 1, to port 21 (N) of function 2 in row 0: above 1's top."""
    # UNDO: stages/references/turned.py `_turns_back`: `return False` at its head
    wires = (_wire(1, (1, 2), (2, 1)),)
    (star,) = _turned(wires, ("a", (9, 1)), ("b", (2,)))
    assert star.wires == frozenset({hid("conductor", 1)})
    assert {ref.port for ref in star.ports} == {hid("port", 12), hid("port", 21)}


def test_conductors_sharing_a_pin_are_one_star_with_one_reference() -> None:
    """Two turned conductors from port 12 make one star, so the pin takes one text."""
    wires = (_wire(1, (1, 2), (2, 1)), _wire(2, (1, 2), (3, 1)))
    (star,) = _turned(wires, ("a", (9, 1)), ("b", (2,)), ("c", (3,)))
    assert star.wires == frozenset({hid("conductor", 1), hid("conductor", 2)})


def test_a_link_of_a_terminal_chain_never_turns_even_where_its_row_is_stacked() -> None:
    """Terminals 1 and 2 of strip X1 are jumpered bottom to bottom, 1 below function 9 and 2 at
    the top of the next column: the S pin of 1 sees 2 above it, a turn for any other wire."""
    # UNDO: stages/references/turned.py `_turns`: drop `or conductor.handle in chains.links`
    wires = (_wire(1, (1, 2), (2, 2)),)
    columns = (("a", (9, 1)), ("b", (2,)))
    assert len(_turned(wires, *columns)) == 1  # control: no strip, the wire turns
    assert _turned(wires, *columns, terminals=frozenset({1, 2})) == ()
