"""`lint_chains`: `LONE_CELL` (a symbol stranded or loose) and `CHAIN_BROKEN` (a cut wire)."""

import dataclasses
from typing import Any

import pytest
from coherence_helpers import group, layout_of, marker
from samples import column, connection, drawn, function_spec, hid, placed

from fransys_layout.geometry import LayoutError
from fransys_layout.lint import lint_chains
from fransys_layout.lint.chains import StageRecords
from fransys_layout.lint.codes import CHAIN_BROKEN, LONE_CELL
from fransys_layout.stages import DrawnFunction, MarkerSide
from fransys_model.kernel import Finding, Severity

_STRANDED = "a symbol stands alone on its page although its column has more cells"
_LOOSE = (
    "a symbol has nothing connected, so it is not drawn: wire 13 and 14, or remove it if it is"
    " not used"
)
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
    functions,
    columns,
    *,
    drawn_functions=_DRAWN,
    loose=(),
    **given,
) -> tuple[Finding, ...]:
    """Lint `functions` in `columns`; `wiring` overrides `markers`, `connections`, `net_groups`."""
    printed = given.pop("printed", None)  # the numbers of the printed sets (model-0201)
    wiring: dict[str, Any] = {"markers": (), "connections": _CHAIN, "net_groups": ()} | given
    layout = layout_of(markers=wiring["markers"], functions=functions)
    records = StageRecords(
        columns, drawn_functions, wiring["connections"], wiring["net_groups"], loose
    )
    return lint_chains(layout, records, printed=printed)


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


@pytest.mark.parametrize(
    ("printed", "expected"),
    [
        pytest.param(None, (_lone(1, _STRANDED),), id="every set"),
        pytest.param(frozenset({1}), (_lone(1, _STRANDED),), id="set 1 printed"),
        pytest.param(frozenset({2}), (), id="set 1 not printed"),
    ],
)
def test_a_lone_cell_on_a_set_nobody_prints_is_not_reported(printed, expected) -> None:
    """model-0201: a look finding names no page of an unprinted set."""
    assert _lint((_F1,), (column("a", (1, 2)),), printed=printed) == expected


# --- LONE_CELL (b): no wired port at all ----------------------------------------------------


def test_a_loose_function_is_one_finding_at_no_page_naming_its_pins() -> None:
    """layout-0218 (A4): function 4 has nothing connected and is placed nowhere: one `LONE_CELL`.

    Its message names the pins to wire; it names no page, since the function is on none.

    # UNDO: lint/chains.py, `lint_chains` leaves out `loose_findings(records.loose)`
    """
    findings = _lint((_F1, _F2), (column("a", (1, 2)),), loose=(function_spec(4),))
    assert findings == (_lone(4, _LOOSE),)


def test_a_placed_function_with_no_wire_is_no_lone_cell_by_itself() -> None:
    """The lint no longer measures wires: only `loose` and a cut column give a `LONE_CELL`."""
    second_set = dataclasses.replace(_F1, drawing_set=2)
    assert _lint((_F1, second_set), (column("a", (1,)),), connections=()) == ()


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
