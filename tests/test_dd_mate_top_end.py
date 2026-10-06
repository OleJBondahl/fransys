"""Deep-dive D8 and D11 (amended 2026-09-24, acceptance 10): a cross-unit mate stands at an end of
its parent's column, and the boundary pin's replica stands outside the column at that end.

At a column's bottom end the replica is below the parent-side pin, the plug's wire leaves upward,
the outline's top edge is on the mating line and the outline stands below the plug. At a column's
top end (the chain enters from the unit edge, so the column runs down from the pin) the replica
is above the parent-side pin, the plug is turned so its wire leaves downward into the column, the
outline's bottom edge is on the mating line and the outline stands above the plug; its title is
below-left when free, else above-left inside D4's top room (page y >= 0).

Built through the `fransys` facade from `examples/demo-parts`; read from `layout.*` records.
The mating line is the middle of the plug's and the replica's origins: the two symbols are turned
face to face, each body reaches from its origin to the line (the convention of
`test_dd_outline_mate_crash.py`, `outline.y * 2 == plug.y + pin.y`).

Wirings of `_relay_on`: `coil_A1` runs plug -> coil (the mate at the column's top end, the coil
stands below the plug); `coil_A2` runs coil -> plug (the mate at the bottom end, the coil above).
"""

from functools import cache
from typing import Any, NamedTuple

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import system_document

from fransys_model.kernel import Severity
from fransys_model.layout import (
    Label,
    Orientation,
    Outline,
    Route,
    SymbolPlacement,
    layout_of,
)
from fransys_model.vocab.tables import functions, ports

_PROJECT: dict[str, Any] = {
    "title": "Mate ends",
    "number": "P-1006",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}
_TOP = "coil_A1"
_BOTTOM = "coil_A2"


def _relay_on(d, plug, kind: str, tag: str, where) -> None:
    """Wire `plug`'s pin 1 to a relay: `coil_A1`/`coil_A2` its coil pin, `contact_11`/`contact_14`
    its first contact's pin."""
    relay = d.item("DEMO-RLY-2CO-24", tag=tag, at=where[0], group=where[1])
    wire = d.wiring(colour="BU", gauge="0.5")
    function, pin = kind.split("_")
    # layout-0112: an unwired contact is not drawn; wire the others so the columns stay as before
    wire(relay.fn("co_2")["21"], relay.fn("co_2")["24"])
    if function == "coil":
        wire(plug["1"], relay.fn("coil")[pin])
        wire(relay.fn("co_1")["11"], relay.fn("co_1")["14"])
    else:
        wire(relay.fn("co_1")[pin], plug["1"])


@cache
def _nested_board(first: str, second: str):
    """A cabinet unit whose plugs J1 and J2 mate the headers of a board unit nested in it, each
    plug wired to a relay of the cabinet: the board's black box holds both mates on one page."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    cab = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    cab.revision(1, date="2026-01-01", text="First release", created="XX")
    c1, group = cab.location("C1", "Cabinet"), d.group("PLC", "PLC")
    board = cab.scope("a2", group=group).unit("demo-io-board", revision=1, interface="1")
    board.revision(1, date="2026-01-01", text="First release", created="XX")
    for n, kind in enumerate((first, second), 1):
        header = board.item("DEMO-CONN-2P", tag=f"J{n}")
        board.boundary(header)
        plug = cab.item("DEMO-CONN-2P", tag=f"J{n}", at=c1, group=group)
        _relay_on(cab, plug, kind, f"K{n}", (c1, group))
        cab.mate(plug, header)
    result = fr.build(parts, d.draft(), system_document())
    assert [f.code for f in result.findings if f.severity is Severity.ERROR] == []
    return result.model


class _Mate(NamedTuple):
    """What the layout drew for the mate `J<n>`: the parent-side pin, the boundary pin's replica
    beside it, the outline holding the replica, its title, the routes of the plug's wire, and the
    other placements of the plug's column."""

    plug: SymbolPlacement
    pin: SymbolPlacement
    outline: Outline
    title: Label
    wires: list[Route]
    column: list[SymbolPlacement]


def _mate(model, n: int) -> _Mate:
    """The drawn mate `J<n>`, all read from the page of the plug."""
    named = functions(model)
    every = list(layout_of(model, SymbolPlacement).values())
    (plug,) = (p for p in every if named[p.function].key[:2] == ("cab", f"J{n}"))
    (pin,) = (
        p
        for p in every
        if p.page == plug.page and named[p.function].key[:3] == ("cab", "a2", f"J{n}")
    )
    (outline,) = (
        o
        for o in layout_of(model, Outline).values()
        if o.page == plug.page and o.x <= pin.x <= o.x + o.width
    )
    (title,) = (
        label
        for label in layout_of(model, Label).values()
        if label.page == plug.page and label.slot == "outline_title" and label.x == outline.x
    )
    plug_ports = {port.id for port in ports(model).values() if port.function == plug.function}
    wires = [
        r
        for r in layout_of(model, Route).values()
        if r.page == plug.page and (r.a in plug_ports or r.b in plug_ports)
    ]
    column = [p for p in every if p.page == plug.page and p.x == plug.x and p not in (plug, pin)]
    assert len(wires) == 1
    return _Mate(plug, pin, outline, title, wires, column)


def _mates(end: str) -> list[_Mate]:
    """Both mates of a board whose plugs are both wired for `end`."""
    model = _nested_board(end, end)
    return [_mate(model, n) for n in (1, 2)]


def test_at_a_top_end_the_replica_stands_above_the_parent_side_pin() -> None:
    """The boundary pin's replica shares the plug's column x but stands above the plug and above
    every other cell of that column: it is outside the column, on the unit-edge side."""
    for mate in _mates(_TOP):
        assert mate.pin.x == mate.plug.x
        assert mate.pin.y < mate.plug.y
        assert mate.column, "the column holds cells besides the pin pair"
        assert mate.pin.y < min(p.y for p in mate.column)


def test_at_a_top_end_the_parent_side_pin_faces_the_replica_and_its_wire_leaves_downward() -> None:
    """The plug is turned round (R180: its wire port on the S side, the replica's body across from
    its body), and no point of its wire's route is above the plug: the wire goes into the column."""
    for mate in _mates(_TOP):
        assert mate.plug.orientation is Orientation.R180
        assert mate.pin.orientation is Orientation.R0
        (wire,) = mate.wires
        assert min(point.y for point in wire.points) >= mate.plug.y


def test_at_a_top_end_the_outline_bottom_edge_is_on_the_mating_line_above_the_plug() -> None:
    """The outline's bottom edge is the mating line (half way between the two origins), the
    replica is inside it, and the plug, whose body reaches from its origin up to the line, is
    outside: the plug's origin is at or below the bottom edge."""
    for mate in _mates(_TOP):
        outline, plug, pin = mate.outline, mate.plug, mate.pin
        assert (outline.y + outline.height) * 2 == plug.y + pin.y
        assert outline.y <= pin.y
        assert outline.y + outline.height <= plug.y


def test_at_a_top_end_the_title_is_below_left_when_free_else_above_left_inside_the_top_room() -> (
    None
):
    """Below-left of a top-end outline is where the first plug stands, so it is never free here:
    the title stands above-left, at the outline's left edge, inside the page (y >= 0). (The
    below-left case cannot arise in this fixture: the two neighbouring top-end mates share one
    outline and one title, and the first plug's column stands under the title's left end.)"""
    mates = _mates(_TOP)
    assert len({m.outline for m in mates}) == 1
    title, outline = mates[0].title, mates[0].outline
    assert title.x == outline.x
    assert title.y >= 0
    assert title.y + title.height <= outline.y
    assert any(title.x <= m.plug.x <= title.x + title.width for m in mates), (
        "below-left would cover a plug"
    )


def test_at_a_bottom_end_nothing_changes() -> None:
    """The control: with the chain entering from the parent's side the replica is below the plug,
    the plug's wire leaves upward, the outline's top edge is on the mating line and the outline
    stands below the plug; its title is below-left, above-left being the plug's own place."""
    for mate in _mates(_BOTTOM):
        outline, plug, pin, title = mate.outline, mate.plug, mate.pin, mate.title
        assert pin.x == plug.x
        assert pin.y > plug.y
        assert plug.orientation is Orientation.R0
        assert pin.orientation is Orientation.R180
        (wire,) = mate.wires
        assert max(point.y for point in wire.points) <= plug.y
        assert outline.y * 2 == plug.y + pin.y
        assert outline.y >= plug.y
        assert outline.y + outline.height >= pin.y
        assert title.x == outline.x
        assert title.y >= outline.y + outline.height
        assert title.x <= plug.x <= title.x + title.width, "above-left would cover the plug"


def test_a_top_end_and_a_bottom_end_mate_in_one_unit_get_two_outlines() -> None:
    """One board with J1 wired for a top end and J2 for a bottom end: two outlines on the page,
    one per end, J1's above its plug and J2's below its plug."""
    # contact_14 faces S like coil_A2: the contact stands above the plug, a bottom end
    model = _nested_board(_TOP, "contact_14")
    top, bottom = _mate(model, 1), _mate(model, 2)
    assert top.plug.page == bottom.plug.page
    assert top.outline != bottom.outline
    on_page = [o for o in layout_of(model, Outline).values() if o.page == top.plug.page]
    assert len(on_page) == 2
    assert top.outline.y + top.outline.height <= top.plug.y
    assert (top.outline.y + top.outline.height) * 2 == top.plug.y + top.pin.y
    assert bottom.outline.y >= bottom.plug.y
    assert bottom.outline.y * 2 == bottom.plug.y + bottom.pin.y
