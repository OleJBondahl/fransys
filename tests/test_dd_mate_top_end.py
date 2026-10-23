"""A cross-unit mate stands at an end of
its parent's column, and the boundary pin's replica stands outside the column at that end.

At a column's bottom end the replica is below the parent-side pin, the plug's wire leaves upward,
the outline's top edge is on the mating line and the outline stands below the plug. At a column's
top end (the chain enters from the unit edge, so the column runs down from the pin) the replica
is above the parent-side pin, the plug is turned so its wire leaves downward into the column, the
outline's bottom edge is on the mating line and the outline stands above the plug; its title is
below-left when free, else above-left inside the top room (page y >= 0).

Built through the `fransys` facade from `examples/demo-parts`; read from the page Drawings.
The mating line is the middle of the plug's and the replica's origins: the two symbols are turned
face to face, each body reaches from its origin to the line (the convention of
`test_dd_outline_mate_crash.py`, `outline.y * 2 == plug.y + pin.y`).

Wirings of `_relay_on`: `coil_A1` runs plug -> coil (the mate at the column's top end, the coil
stands below the plug); `coil_A2` runs coil -> plug (the mate at the bottom end, the coil above).
"""

from functools import cache
from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
import fransys_author
import fransys_parts
from _drawn_pages import drawn_pages
from _model_build_cover import layout_trigger_document

from fransys_model.kernel import Severity

if TYPE_CHECKING:
    from fransys_layout.drawing import Drawing, DrawnOutline, DrawnSymbol, DrawnText, DrawnWire

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
    result = fr.build(parts, d.draft(), layout_trigger_document())
    assert [f.code for f in result.findings if f.severity is Severity.ERROR] == []
    return result.model


class _Mate(NamedTuple):
    """What the core drew for the mate `J<n>`: the parent-side pin, the boundary pin's replica
    beside it, the outline holding the replica, its title, the wires of the plug's column, and the
    other symbols of the plug's column."""

    plug: DrawnSymbol
    pin: DrawnSymbol
    outline: DrawnOutline
    title: DrawnText
    wires: list[DrawnWire]
    column: list[DrawnSymbol]


def _box(outline: DrawnOutline) -> tuple[int, int, int, int]:
    """The outline's (x, y, width, height)."""
    xs, ys = [x for x, _ in outline.points], [y for _, y in outline.points]
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def _plug_page(model, n: int) -> tuple[Drawing, DrawnText]:
    """The page that prints the plug's tag `-J<n>:1`, and that tag."""
    found = [
        (drawing, text)
        for drawing in drawn_pages(model).values()
        for text in drawing.texts
        if text.text == f"-J{n}:1"
    ]
    (one,) = found
    return one


def _mate(model, n: int) -> _Mate:
    """The drawn mate `J<n>`, all read from the page of the plug."""
    drawing, tag = _plug_page(model, n)
    boxes = [s for s in drawing.symbols if s.key.startswith("connector")]
    column_x = min((s.x for s in boxes), key=lambda x: abs(x - tag.box.x - 56))
    same = [s for s in boxes if s.x == column_x]
    plug = min(same, key=lambda s: abs(s.y - tag.box.y - 24))
    (pin,) = (s for s in same if s is not plug)
    (outline,) = (o for o in drawing.outlines if _box(o)[0] <= pin.x <= _box(o)[0] + _box(o)[2])
    title = outline.label
    assert title is not None
    wires = [w for w in drawing.wires if any(x == plug.x for x, _ in w.points)]
    column = [s for s in drawing.symbols if s.x == plug.x and s not in (plug, pin)]
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
        assert mate.plug.orient == "R180"
        assert mate.pin.orient == "R0"
        (wire,) = mate.wires
        assert min(y for _, y in wire.points) >= mate.plug.y


def test_at_a_top_end_the_outline_bottom_edge_is_on_the_mating_line_above_the_plug() -> None:
    """The outline's bottom edge is the mating line (half way between the two origins), the
    replica is inside it, and the plug, whose body reaches from its origin up to the line, is
    outside: the plug's origin is at or below the bottom edge."""
    for mate in _mates(_TOP):
        plug, pin = mate.plug, mate.pin
        _, oy, _, oh = _box(mate.outline)
        assert (oy + oh) * 2 == plug.y + pin.y
        assert oy <= pin.y
        assert oy + oh <= plug.y


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
    ox, oy, _, _ = _box(outline)
    assert title.box.x == ox
    assert title.box.y >= 0
    assert title.box.y + title.box.h <= oy
    assert any(title.box.x <= m.plug.x <= title.box.x + title.box.w for m in mates), (
        "below-left would cover a plug"
    )


def test_at_a_bottom_end_nothing_changes() -> None:
    """The control: with the chain entering from the parent's side the replica is below the plug,
    the plug's wire leaves upward, the outline's top edge is on the mating line and the outline
    stands below the plug; its title is below-left, above-left being the plug's own place."""
    for mate in _mates(_BOTTOM):
        plug, pin, title = mate.plug, mate.pin, mate.title
        ox, oy, _, oh = _box(mate.outline)
        assert pin.x == plug.x
        assert pin.y > plug.y
        assert plug.orient == "R0"
        assert pin.orient == "R180"
        (wire,) = mate.wires
        assert max(y for _, y in wire.points) <= plug.y
        assert oy * 2 == plug.y + pin.y
        assert oy >= plug.y
        assert oy + oh >= pin.y
        assert title.box.x == ox
        assert title.box.y >= oy + oh
        assert title.box.x <= plug.x <= title.box.x + title.box.w, "above-left would cover the plug"


def test_a_top_end_and_a_bottom_end_mate_in_one_unit_get_two_outlines() -> None:
    """One board with J1 wired for a top end and J2 for a bottom end: two outlines on the page,
    one per end, J1's above its plug and J2's below its plug."""
    # contact_14 faces S like coil_A2: the contact stands above the plug, a bottom end
    model = _nested_board(_TOP, "contact_14")
    top, bottom = _mate(model, 1), _mate(model, 2)
    drawing, _ = _plug_page(model, 1)
    assert _plug_page(model, 2)[0] is drawing
    assert top.outline != bottom.outline
    assert len(drawing.outlines) == 2
    _, ty, _, th = _box(top.outline)
    _, by, _, _ = _box(bottom.outline)
    assert ty + th <= top.plug.y
    assert (ty + th) * 2 == top.plug.y + top.pin.y
    assert by >= bottom.plug.y
    assert by * 2 == bottom.plug.y + bottom.pin.y
