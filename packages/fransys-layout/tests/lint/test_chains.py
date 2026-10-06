"""`lint_chains`: `LONE_CELL` (a symbol stranded or unwired) and `CHAIN_BROKEN` (a cut wire)."""

import dataclasses
import itertools
from typing import Any

import pytest
from coherence_helpers import group, layout_of, marker
from samples import column, connection, drawn, hid, placed

from fransys_layout.geometry import LayoutError
from fransys_layout.lint import lint_chains
from fransys_layout.lint.chains import StageRecords
from fransys_layout.lint.codes import ALL_CODES, CHAIN_BROKEN, LONE_CELL
from fransys_layout.stages import DrawnFunction, MarkerSide
from fransys_layout.stages.types import MatedFunctions
from fransys_model.kernel import Finding, Severity

_STRANDED = "a symbol stands alone on its page although its column has more cells"
_UNWIRED = "a symbol has no drawn conductor at all"
_CUT = "a connection between two cells was cut into a marker pair"

# Function n has ports 10n + 1 and 10n + 2. Connection 1 wires ports 12 and 21, connection 2
# wires 22 and 31: functions 1 to 3 are wired, function 4 is not.
_CHAIN = (connection(1, 1, 2), connection(2, 2, 3))
_DRAWN = tuple(drawn(n) for n in (1, 2, 3, 4))
_F1 = placed(1, x=104, y=96)
_F2 = placed(2, x=104, y=304)


def _no_pole(number: int) -> DrawnFunction:
    """Function `number` drawn with no through path: a box, holding no D1 pole."""
    base = drawn(number)
    return dataclasses.replace(base, geometry=dataclasses.replace(base.geometry, through=None))


def _lone(number: int, message: str) -> Finding:
    return Finding(
        code=LONE_CELL,
        severity=Severity.WARNING,
        subjects=(hid("function", number),),
        message=message,
    )


def _broken(conductor: int, a: int, b: int) -> Finding:
    return Finding(
        code=CHAIN_BROKEN,
        severity=Severity.WARNING,
        subjects=(hid("conductor", conductor), hid("function", a), hid("function", b)),
        message=_CUT,
    )


def _marker(conductor: int, port: int, side: MarkerSide = MarkerSide.OWNER, *, page: int = 1):
    return marker(hid("conductor", conductor), port, side, page=page, at=(120, 96))


def _lint(
    functions, columns, *, drawn_functions=_DRAWN, mates=(), open_ends=frozenset(), **given
) -> tuple[Finding, ...]:
    """Lint `functions` in `columns`; `wiring` overrides `markers`, `connections`, `net_groups`."""
    wiring: dict[str, Any] = {"markers": (), "connections": _CHAIN, "net_groups": ()} | given
    layout = layout_of(markers=wiring["markers"], functions=functions)
    records = StageRecords(
        columns, drawn_functions, wiring["connections"], wiring["net_groups"], mates
    )
    return lint_chains(layout, records, open_ends=open_ends)


# --- LONE_CELL (a): the column was cut across pages -----------------------------------------


@pytest.mark.parametrize(
    ("columns", "functions", "expected"),
    [
        pytest.param(
            (column("a", (1, 2)),), (_F1,), (_lone(1, _STRANDED),), id="one cell alone on the page"
        ),
        pytest.param((column("a", (1, 2)),), (_F1, _F2), (), id="both cells on the page"),
        pytest.param(
            (column("a", (1, 2)),),
            (_F1, placed(2, x=104, y=96, page=2)),
            (_lone(1, _STRANDED), _lone(2, _STRANDED)),
            id="cut over two pages: each page's lone cell",
        ),
        pytest.param(
            (column("a", (1, 2, 3)),), (_F1, _F2), (), id="three cells, two placed: not alone"
        ),
        pytest.param((column("a", (1,)),), (_F1,), (), id="a one-cell column is no cut"),
    ],
)
def test_a_column_cut_across_pages_strands_its_lone_cell(columns, functions, expected) -> None:
    """A placed function alone in its column on the page fires only if the column has more."""
    assert _lint(functions, columns) == expected


def test_a_lone_terminal_in_a_multi_cell_column_fires() -> None:
    """No terminal exemption: the same shape fires for a terminal."""
    kinds = (drawn(1, kind="terminal"), *_DRAWN[1:])
    assert _lint((_F1,), (column("a", (1, 2)),), drawn_functions=kinds) == (_lone(1, _STRANDED),)


def test_a_one_cell_column_whose_only_wire_is_a_marker_is_silent() -> None:
    """Under D9 a symbol may stand alone when its conductors end in markers."""
    findings = _lint(
        (_F1,), (column("a", (1,)),), markers=(_marker(1, 12, MarkerSide.USER),), connections=()
    )
    assert findings == ()


# --- LONE_CELL (b): no wired port at all ----------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "connections", "net_groups", "markers", "expected"),
    [
        pytest.param("contact_no", (), (), (), (_lone(1, _UNWIRED),), id="nothing wires it"),
        pytest.param("terminal", (), (), (), (_lone(1, _UNWIRED),), id="a terminal fires too"),
        pytest.param("contact_no", (), (), (_marker(1, 12),), (), id="port wired only by a marker"),
        pytest.param(
            "contact_no", (connection(1, 1, 2),), (), (), (), id="port wired only by a connection"
        ),
        pytest.param(
            "contact_no", (), (group(1, ((1, 11),)),), (), (), id="port wired only by a net group"
        ),
        pytest.param(
            "contact_no",
            (connection(1, 3, 4),),
            (group(1, ((3, 31),)),),
            (_marker(1, 32, MarkerSide.USER),),
            (_lone(1, _UNWIRED),),
            id="wires of other functions do not count",
        ),
    ],
)
def test_a_placed_function_with_no_wired_port_fires(
    kind, connections, net_groups, markers, expected
) -> None:
    """Function 1 stands in a one-cell column, so only rule (b) can apply to it."""
    kinds = (drawn(1, kind=kind), *_DRAWN[1:])
    findings = _lint(
        (_F1,),
        (column("a", (1,)),),
        markers=markers,
        connections=connections,
        net_groups=net_groups,
        drawn_functions=kinds,
    )
    assert findings == expected


def test_an_unwired_function_fires_in_a_column_of_two() -> None:
    """Both cells are on the page; function 2 is wired by nothing, function 1 by a connection."""
    findings = _lint((_F1, _F2), (column("a", (1, 2)),), connections=(connection(1, 1, 3),))
    assert findings == (_lone(2, _UNWIRED),)


def _mate(a: int, b: int) -> tuple[MatedFunctions, ...]:
    return (MatedFunctions(a=hid("function", a), b=hid("function", b)),)


def test_an_unwired_function_whose_mate_is_wired_is_silent() -> None:
    """A mated pin is wired through its mate: function 4 has no wire, function 1 has one."""
    functions = (_F1, placed(4, x=104, y=304))
    assert _lint(functions, (column("a", (1, 4)),)) == (_lone(4, _UNWIRED),)
    assert _lint(functions, (column("a", (1, 4)),), mates=_mate(4, 1)) == ()
    assert _lint(functions, (column("a", (1, 4)),), mates=_mate(1, 4)) == ()


def test_an_unwired_function_whose_mate_is_also_unwired_still_fires() -> None:
    """Functions 1 and 4 are mated and neither is on any wire."""
    functions = (_F1, placed(4, x=104, y=304))
    findings = _lint(
        functions, (column("a", (1, 4)),), connections=(connection(2, 2, 3),), mates=_mate(4, 1)
    )
    assert findings == (_lone(1, _UNWIRED), _lone(4, _UNWIRED))


def test_a_stranded_and_unwired_function_gives_one_finding_the_stranded_one() -> None:
    """Both (a) and (b) hold for function 1: only (a) is reported."""
    assert _lint((_F1,), (column("a", (1, 2)),), connections=()) == (_lone(1, _STRANDED),)


def test_a_symbol_placed_in_two_drawing_sets_is_reported_once() -> None:
    """Function 1 has no wire at all and stands in drawing sets 1 and 2: one finding, not two.

    Rule (b) is a fact of the symbol, not of a placement; a black-box stand-in in a parent's set
    is the same symbol again.

    # UNDO: lint/chains.py, drop the `seen` test (one finding per placement again)
    """
    second_set = dataclasses.replace(_F1, drawing_set=2)
    findings = _lint((_F1, second_set), (column("a", (1,)),), connections=())
    assert findings == (_lone(1, _UNWIRED),)


def test_an_open_end_is_no_lone_cell_when_unwired_but_a_twin_is() -> None:
    """A boundary function's outside is open (units spec U2): function 1 is silent, 4 fires.

    Both stand in a one-cell column and have no wire; only function 1 is in `open_ends`.

    # UNDO: lint/chains.py, ignore `open_ends`
    """
    functions = (_F1, placed(4, x=104, y=304, name="b"))
    columns = (column("a", (1,)), column("b", (4,)))
    ends = frozenset({hid("function", 1)})
    assert _lint(functions, columns, connections=(), open_ends=ends) == (_lone(4, _UNWIRED),)
    assert _lint(functions, columns, connections=()) == (_lone(1, _UNWIRED), _lone(4, _UNWIRED))


def test_an_open_end_stranded_by_a_column_cut_still_fires() -> None:
    """The exemption is for rule (b) only: a column cut across pages strands an open end too."""
    ends = frozenset({hid("function", 1)})
    assert _lint((_F1,), (column("a", (1, 2)),), open_ends=ends) == (_lone(1, _STRANDED),)


# --- CHAIN_BROKEN ---------------------------------------------------------------------------

_COLUMNS = (column("a", (1, 2)), column("b", (3, 4)))
_PAIR = (_F1, _F2)


def _cut(**overrides) -> tuple[Finding, ...]:
    """Functions 1 and 2, both on the page, wired by connection 1, with an owner marker at 12."""
    options = {"markers": (_marker(1, 12),), "connections": (connection(1, 1, 2),)} | overrides
    return _lint(_PAIR, _COLUMNS, **options)


def test_an_owner_marker_on_a_two_port_net_between_two_poles_fires() -> None:
    """A pole link (D1) cut into markers, as a page split would: the exact subjects."""
    findings = _cut()
    assert findings == (_broken(1, 1, 2),)
    assert findings[0].subjects == (hid("conductor", 1), hid("function", 1), hid("function", 2))


@pytest.mark.parametrize("box", [1, 2])
def test_a_box_to_box_two_port_net_may_be_cut(box: int) -> None:
    """D1: only a net of exactly two POLE ports links two poles.

    Function `box` is drawn with no through path (a box has none), so its end is no pole
    port, whatever its net's size. A 2-port net that is not a pole link never fires
    `CHAIN_BROKEN`, even between two functions neither of which is a terminal.
    """
    kinds = tuple(_no_pole(n) if n == box else drawn(n) for n in (1, 2))
    assert _cut(drawn_functions=kinds) == ()


def test_a_terminal_end_may_be_cut() -> None:
    """A real terminal symbol has no through path (`terminal` in the library): no pole port."""
    kinds = (_no_pole(1), drawn(2))
    assert _cut(drawn_functions=kinds) == ()


@pytest.mark.parametrize(
    ("markers", "net_groups", "connections"),
    [
        pytest.param(
            (_marker(1, 12, MarkerSide.USER),), (), (connection(1, 1, 2),), id="user-side marker"
        ),
        pytest.param(
            (dataclasses.replace(_marker(1, 12), star="ref"),),
            (),
            (connection(1, 1, 2),),
            id="star marker",
        ),
        pytest.param(
            (_marker(1, 12),),
            (group(9, ((1, 12), (2, 21), (3, 31))),),
            (connection(1, 1, 2),),
            id="three-port net",
        ),
        pytest.param((_marker(7, 12),), (), (connection(1, 1, 2),), id="unknown connection"),
    ],
)
def test_a_marker_that_is_no_cut_of_a_two_port_net_is_silent(
    markers, net_groups, connections
) -> None:
    """Each shape differs from the firing one by exactly one property."""
    assert _cut(markers=markers, net_groups=net_groups, connections=connections) == ()


def test_the_two_port_net_group_of_a_connection_still_counts_two_ports() -> None:
    """A net group naming only the connection's own ports adds no port."""
    assert _cut(net_groups=(group(9, ((1, 12), (2, 21))),)) == (_broken(1, 1, 2),)


def test_two_markers_of_two_connections_give_two_sorted_findings() -> None:
    """One finding per connection, in `(code, subjects)` order."""
    findings = _lint(
        (*_PAIR, placed(3, x=304, y=96, name="b"), placed(4, x=304, y=304, name="b")),
        _COLUMNS,
        markers=(_marker(2, 32), _marker(1, 12)),
        connections=(connection(2, 3, 4), connection(1, 1, 2)),
    )
    assert findings == (_broken(1, 1, 2), _broken(2, 3, 4))


def test_two_markers_of_one_connection_give_one_finding() -> None:
    """A connection cut into a pair on two pages is reported once."""
    markers = (_marker(1, 12), _marker(1, 12, page=2))
    assert _cut(markers=markers) == (_broken(1, 1, 2),)


# --- both kinds together --------------------------------------------------------------------


def test_the_result_does_not_depend_on_input_order() -> None:
    """A cut column strands function 3 and severs both connections: 2 broken, 1 lone."""
    functions = (_F1, _F2, placed(3, x=304, y=96, name="b"))
    markers = (_marker(1, 12), _marker(2, 32))
    connections = (connection(1, 1, 2), connection(2, 3, 4))
    results = {
        _lint(ordered, _COLUMNS, markers=marked, connections=wired)
        for ordered in itertools.permutations(functions)
        for marked in itertools.permutations(markers)
        for wired in itertools.permutations(connections)
    }
    assert results == {(_broken(1, 1, 2), _broken(2, 3, 4), _lone(3, _STRANDED))}


# --- refusals and codes ---------------------------------------------------------------------


def test_a_placed_column_without_a_stage_column_raises() -> None:
    """Function 1 is placed in column `z`, which no `Column` has."""
    with pytest.raises(LayoutError, match="no stage column"):
        _lint((placed(1, x=104, y=96, name="z"),), _COLUMNS)


def test_a_placed_function_without_a_drawn_function_raises() -> None:
    """Function 9 is placed and nothing draws it."""
    with pytest.raises(LayoutError, match="no drawn function"):
        _lint((_F1, placed(9, x=104, y=96)), _COLUMNS)


def test_the_codes_are_listed_and_warnings() -> None:
    """Both codes are in `ALL_CODES` and every finding here is a `WARNING`."""
    assert {LONE_CELL, CHAIN_BROKEN} <= set(ALL_CODES)
    assert {one.severity for one in (_lone(1, _UNWIRED), _broken(1, 1, 2))} == {Severity.WARNING}
