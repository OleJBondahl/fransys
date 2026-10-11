"""`lint_chains`: `LONE_CELL` (a symbol stranded or unwired) and `CHAIN_BROKEN` (a cut wire)."""

import dataclasses
from typing import Any

import pytest
from coherence_helpers import group, layout_of, marker
from samples import column, connection, drawn, hid, placed

from fransys_layout.geometry import LayoutError
from fransys_layout.lint import lint_chains
from fransys_layout.lint.chains import StageRecords
from fransys_layout.lint.codes import CHAIN_BROKEN, LONE_CELL
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


# --- LONE_CELL (b): no wired port at all ----------------------------------------------------


def _mate(a: int, b: int) -> tuple[MatedFunctions, ...]:
    return (MatedFunctions(a=hid("function", a), b=hid("function", b)),)


def test_a_symbol_placed_in_two_drawing_sets_is_reported_once() -> None:
    """Function 1 has no wire at all and stands in drawing sets 1 and 2: one finding, not two.

    Rule (b) is a fact of the symbol, not of a placement; a black-box stand-in in a parent's set
    is the same symbol again.

    # UNDO: lint/chains.py, drop the `seen` test (one finding per placement again)
    """
    second_set = dataclasses.replace(_F1, drawing_set=2)
    findings = _lint((_F1, second_set), (column("a", (1,)),), connections=())
    assert findings == (_lone(1, _UNWIRED),)


# --- CHAIN_BROKEN ---------------------------------------------------------------------------

_COLUMNS = (column("a", (1, 2)), column("b", (3, 4)))
_PAIR = (_F1, _F2)


def _cut(**overrides) -> tuple[Finding, ...]:
    """Functions 1 and 2, both on the page, wired by connection 1, with an owner marker at 12."""
    options = {"markers": (_marker(1, 12),), "connections": (connection(1, 1, 2),)} | overrides
    return _lint(_PAIR, _COLUMNS, **options)


def test_a_terminal_end_may_be_cut() -> None:
    """A real terminal symbol has no through path (`terminal` in the library): no pole port."""
    kinds = (_no_pole(1), drawn(2))
    assert _cut(drawn_functions=kinds) == ()


def test_the_two_port_net_group_of_a_connection_still_counts_two_ports() -> None:
    """A net group naming only the connection's own ports adds no port."""
    assert _cut(net_groups=(group(9, ((1, 12), (2, 21))),)) == (_broken(1, 1, 2),)


_COIL, _CONTACT = drawn(1, kind="coil"), drawn(2, kind="contact_no")


def _split(kinds, page: int) -> tuple[Finding, ...]:
    """Functions 1 and 2 of `kinds`, function 2 on page `page`, wired by an owner-marked link."""
    return _lint(
        (_F1, placed(2, x=104, y=96, page=page, name="b")),
        (column("a", (1,)), column("b", (2,))),
        drawn_functions=kinds,
        markers=(_marker(1, 12),),
        connections=(connection(1, 1, 2),),
    )


def test_a_coil_to_contact_link_cut_by_a_page_split_is_no_broken_chain() -> None:
    """The contact's image under the coil and the cross-references are the intended IEC split."""
    # UNDO: lint/chains.py `_split_by_pages`: `return False` at its head
    assert _split((_COIL, _CONTACT), page=2) == ()
    assert _split((_CONTACT, _COIL), page=2) == ()


def test_a_coil_to_contact_link_on_one_page_is_still_a_broken_chain() -> None:
    assert _split((_COIL, _CONTACT), page=1) == (_broken(1, 1, 2),)


def test_a_link_between_two_contacts_cut_by_a_page_split_is_still_a_broken_chain() -> None:
    assert _split((drawn(1), _CONTACT), page=2) == (_broken(1, 1, 2),)


# --- both kinds together --------------------------------------------------------------------


# --- refusals and codes ---------------------------------------------------------------------


def test_a_placed_column_without_a_stage_column_raises() -> None:
    """Function 1 is placed in column `z`, which no `Column` has."""
    with pytest.raises(LayoutError, match="no stage column"):
        _lint((placed(1, x=104, y=96, name="z"),), _COLUMNS)


def test_a_placed_function_without_a_drawn_function_raises() -> None:
    """Function 9 is placed and nothing draws it."""
    with pytest.raises(LayoutError, match="no drawn function"):
        _lint((_F1, placed(9, x=104, y=96)), _COLUMNS)
