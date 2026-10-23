"""A legal model must not crash `unit_outlines`. A unit's black box on a page can hold
pins of two mates whose chains enter from opposite sides; the top edge came from one mate and the
bottom edge from another, so the outline's height came out negative ("box size must not be
negative") or zero ("an outline's height must be positive").
A mate stands at the end of its parent's column that the chain enters from; the
outline's edge toward the plug sits on the mating line (the top edge at a bottom end, the bottom
edge at a top end), and mates at opposite ends stand in two outlines, so no outline mixes the
two edges.

Built through the `fransys` facade from `examples/demo-parts`; read from the page Drawings.
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from _drawn_pages import drawn_pages
from _model_build_cover import layout_trigger_document

from fransys_model.derive import item_designation
from fransys_model.kernel import Severity
from fransys_model.vocab.tables import items

_PROJECT: dict[str, Any] = {
    "title": "Outline crash",
    "number": "P-1005",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _relay_on(d, plug, kind: str, tag: str, where) -> None:
    """Wire `plug`'s pin 1 to a relay: `coil_A1`/`coil_A2` its coil pin, `contact_11`/`contact_14`
    its first contact's pin."""
    relay = d.item("DEMO-RLY-2CO-24", tag=tag, at=where[0], group=where[1])
    wire = d.wiring(colour="BU", gauge="0.5")
    function, pin = kind.split("_")
    if function == "coil":
        wire(plug["1"], relay.fn("coil")[pin])
    else:
        wire(relay.fn("co_1")[pin], plug["1"])


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
    return result.model, ("cab", "a2")


def _two_boundary_connectors():
    """A cabinet unit with boundary connectors X1 and X2, each mated to a plug of its own
    top-level harness: X1's plug leaves by a cable core, X2's is wired to a relay coil."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    cab = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    cab.revision(1, date="2026-01-01", text="First release", created="XX")
    c1, group = cab.location("C1", "Cabinet"), d.group("PLC", "PLC")
    far = d.location("FLD", "Field")
    for n in (1, 2):
        header = cab.item("DEMO-CONN-2P", tag=f"X{n}", at=c1, group=group)
        cab.boundary(header)
        harness = d.harness(name=f"w{n}", tag=f"W{n}", at=c1, group=group)
        plug = d.item("DEMO-CONN-2P", tag=f"P{n}", parent=harness, at=c1, group=group)
        if n == 1:
            end = d.item("DEMO-CONN-2P", tag="Q1", parent=harness, at=far, group=group)
            cable = d.cable("DEMO-CBL-4G1.5", name="c1", parent=harness, at=c1)
            cable.core(1, plug["1"], end["1"])
        else:
            _relay_on(d, plug, "coil_A1", "K2", (c1, group))
        d.mate(plug, header)
    return fr.build(parts, d.draft(), layout_trigger_document()).model, ("cab",)


def _symbols(model, key):
    """(drawing, symbols) of the connector symbols tagged for the item whose key ends in `key`,
    read as the symbols in the column of the item's tag text `-<designation>:1`."""
    (item,) = (i for i in items(model).values() if i.key[-len(key) :] == key)
    tag = f"-{item_designation(model, item.id)}:1"
    for drawing in drawn_pages(model).values():
        for text in drawing.texts:
            if text.text == tag:
                boxes = [s for s in drawing.symbols if s.key.startswith("connector")]
                x = min((s.x for s in boxes), key=lambda x: abs(x - text.box.x - 56))
                return drawing, [s for s in boxes if s.x == x], text
    return None, [], None


def _assert_edge_on_the_mating_line(model, scope, ends: tuple[str, str]) -> None:
    """Each pair (plug `J<n>`/`P<n>`, boundary pin) stands at the end `ends[n - 1]` of the plug's
    column: at `"bottom"` the plug is above the boundary pin and the top edge of the outline
    holding the pair is the mating line (halfway between the two pins); at `"top"` the plug is
    below the pin and the outline's bottom edge is the mating line. The two ends stand in two
    outlines, each of positive height."""
    pages = [d for d in drawn_pages(model).values() if d.outlines]
    (drawing,) = pages
    assert len(drawing.outlines) == len(set(ends))
    for n, end in enumerate(ends, 1):
        key = (f"P{n}",) if len(scope) == 1 else ("cab", f"J{n}")
        _, column, tag = _symbols(model, key)
        plug = min(column, key=lambda s: abs(s.y - tag.box.y - 24))
        (pin,) = (s for s in column if s is not plug)
        (outline,) = (
            o
            for o in drawing.outlines
            if min(x for x, _ in o.points) <= pin.x <= max(x for x, _ in o.points)
        )
        top, bottom = min(y for _, y in outline.points), max(y for _, y in outline.points)
        assert bottom > top
        if end == "top":
            assert pin.y < plug.y
            assert bottom * 2 == plug.y + pin.y
        else:
            assert plug.y < pin.y
            assert top * 2 == plug.y + pin.y


@pytest.mark.parametrize(
    ("first", "second", "ends"),
    [
        # 11 faces N like coil_A1 (a top end); 14 faces S like coil_A2 (a bottom end)
        ("coil_A1", "contact_14", ("top", "bottom")),
        ("coil_A2", "contact_11", ("bottom", "top")),
    ],
)
def test_a_boards_two_mates_facing_opposite_ways_build_with_the_edge_on_the_mating_line(
    first, second, ends
) -> None:
    """One box holds a mate whose chain enters from the unit side and one from the parent side:
    the outlines must not go negative, and each one's edge toward its plug stands on the mating
    line."""
    # UNDO: fransys_layout/stages/_chain_walk.py: `_note_edges`
    #     `out.edge_top.add(p)` is skipped (every mate at a bottom end again)
    model, scope = _nested_board(first, second)
    _assert_edge_on_the_mating_line(model, scope, ends)


def test_two_boundary_connectors_of_different_chain_directions_build_with_a_positive_outline() -> (
    None
):
    """The zero-height variant: two boundary connectors mated to top-level harness plugs, one
    plug wired to a cable core and one to a relay coil, stand at opposite ends: two outlines."""
    # UNDO: fransys_layout/stages/_chain_walk.py: `_note_edges`
    #     `out.edge_top.add(p)` is skipped (every mate at a bottom end again)
    model, scope = _two_boundary_connectors()
    _assert_edge_on_the_mating_line(model, scope, ("bottom", "top"))
