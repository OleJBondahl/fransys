"""T6 and T7: the marker end table and the link case table, one row hit alone, and their order."""

import dataclasses
from typing import Any

import pytest
from samples import drawn, hid

from fransys_layout.conventions import FACTS, first_match
from fransys_layout.conventions.references import LINK_CASE, MARKER_ENDS
from fransys_layout.stages import LinkCase, MarkerSide, PortRef
from fransys_layout.stages.references.ends import EndRead, marker_end
from fransys_layout.stages.references.link_case import CutRead, link_case
from fransys_layout.stages.references.types import Cut, Leave, LinkWorld, PortEnd

UNIT_A, UNIT_B = hid("unit", 1), hid("unit", 2)
PAGE_1, PAGE_2 = (1, 1), (2, 1)


def _read(
    *, units: tuple = (UNIT_A, UNIT_A), terminal_seated: bool = False, same_item: bool = False
) -> CutRead:
    """A cut of function 1 on `PAGE_1` to function 2 on `PAGE_2`; each fact set by a flag."""
    first, second = drawn(1), drawn(2)
    if same_item:
        second = dataclasses.replace(second, item=first.item)
    ends = tuple(
        PortEnd(ref=PortRef(function=one.function, port=one.ports[0].port), page=page)
        for one, page in ((first, PAGE_1), (second, PAGE_2))
    )
    seats = {PAGE_1: ("a",), PAGE_2: ("b",)}
    terminal = hid("function", 9)
    where: dict[Any, Any] = {first.function: {PAGE_1: ("a",)}, second.function: {PAGE_2: ("b",)}}
    where[terminal] = seats if terminal_seated else {PAGE_1: ("a",)}
    net = hid("net", 1)
    return CutRead(
        Cut(connection=hid("conductor", 1), physical_net=net, ends=(ends[0], ends[1])),
        {net: frozenset({terminal})},
        LinkWorld(where=where, drawn_of={first.function: first, second.function: second}),
        {1: units[0], 2: units[1]},
    )


@pytest.mark.parametrize(
    ("read", "row", "case"),
    [
        (_read(units=(UNIT_A, UNIT_B)), "T7.1", LinkCase.CROSS_UNIT),
        (_read(terminal_seated=True), "T7.2", LinkCase.TERMINAL_ECHO),
        (_read(same_item=True), "T7.3", LinkCase.TAG_ECHO),
        (_read(), "T7.4", LinkCase.SEVERED),
    ],
)
def test_each_link_case_row_is_hit_alone(read: CutRead, row: str, case: LinkCase) -> None:
    """T7.1 to T7.4: only the facts of its row hold, and the stage maps the row to its case."""
    hit = first_match(LINK_CASE, read, FACTS)
    assert hit is not None
    assert hit.id == row
    assert link_case(read) is case


def test_the_link_case_order_decides_when_two_rows_hold() -> None:
    """Can fail: across units and one item is cross-unit; rows 1 and 3 swapped, tag echo."""
    read = _read(units=(UNIT_A, UNIT_B), same_item=True)
    assert link_case(read) is LinkCase.CROSS_UNIT
    rows = LINK_CASE.rows
    swapped = LINK_CASE._replace(rows=(rows[2], rows[1], rows[0], rows[3]))
    hit = first_match(swapped, read, FACTS)
    assert hit is not None
    assert hit.then == "tag_echo"


@pytest.mark.parametrize(
    ("read", "row", "end"),
    [
        (EndRead("star_ref", by_designation=True), "T6.1", (MarkerSide.OWNER, Leave.PORT)),
        (EndRead("star_ref"), "T6.2", (MarkerSide.OWNER, Leave.FREE)),
        (EndRead("star_branch"), "T6.3", (MarkerSide.USER, Leave.FREE_OR_PORT)),
        (
            EndRead("split", at_home=True, terminal=True),
            "T6.4",
            (MarkerSide.OWNER, Leave.SOUTH),
        ),
        (EndRead("split", terminal=True), "T6.5", (MarkerSide.USER, Leave.NORTH)),
        (EndRead("cut", earlier=True), "T6.6", (MarkerSide.OWNER, Leave.PORT)),
        (EndRead("cut"), "T6.7", (MarkerSide.USER, Leave.PORT)),
        (EndRead("off_stub"), "T6.8", (MarkerSide.OWNER, Leave.PORT)),
        (EndRead("rail_branch"), "T6.9", (MarkerSide.USER, Leave.FREE_OR_PORT)),
    ],
)
def test_each_marker_end_row_is_hit_alone(
    read: EndRead, row: str, end: tuple[MarkerSide, Leave]
) -> None:
    """T6.1 to T6.9: the row that holds is the named one, and its strings map to the enums."""
    hit = first_match(MARKER_ENDS, read, FACTS)
    assert hit is not None
    assert hit.id == row
    assert marker_end(read) == end


def test_a_star_reference_by_designation_needs_the_first_row() -> None:
    """Can fail: with T6.2 first, a reference by designation would leave by a free port."""
    rows = MARKER_ENDS.rows
    swapped = MARKER_ENDS._replace(rows=(rows[1], rows[0], *rows[2:]))
    hit = first_match(swapped, EndRead("star_ref", by_designation=True), FACTS)
    assert hit is not None
    assert hit.then == ("owner", "free")
