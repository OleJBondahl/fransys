"""LD7 with LD6 (layout-0081): on a unit's own drawing set no stub label names an item of that unit.

A unit is one drawing, so a wire between two of its own items is a wire (or a marker pair where a
page break cuts it), never a stub, even when the two ends stand at two top-level locations. The
unit `u2-board` has a root board `-U2` at +A with a labelled connector `-X1` (the unit's
boundary, on the board), and a lamp `-L1` mounted on the board at +B. `X1:2` is wired to `L1:2`
(before: two stubs, `+A-U2-X1:2` beside the lamp and `+B-U2-L1:2` beside the connector) and
`X1:1` to a top-level plug `-P1` at +C (a wire that leaves the drawing: still a stub, the
control that keeps this test from passing on a design with no stubs at all).

Built through the `fransys` facade from `examples/demo-parts`; read from `layout.*` records.
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import system_document

from fransys_model.derive.drawing_text import marker_text
from fransys_model.kernel import Severity
from fransys_model.layout import DrawingSet, LinkMarker, Page, StarKind, layout_of
from fransys_model.vocab.tables import functions, items, ports

_PROJECT: dict[str, Any] = {
    "title": "Unit without self stubs",
    "number": "P-1012",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _build():
    """The design of the module docstring."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    u = d.scope("u").unit("u2-board", revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    side_a, side_b = u.location("A", "Side A"), u.location("B", "Side B")
    group = u.group("BRD", "Board")
    board = u.item("DEMO-PCB-IO", tag="U2", at=side_a, group=group)
    x1 = u.item("DEMO-CONN-2P", tag="X1", parent=board, at=side_a, group=group)
    lamp = u.item("DEMO-LAMP-24", tag="L1", parent=board, at=side_b, group=group)
    u.boundary(x1)
    plug = d.item("DEMO-CONN-2P", tag="P1", at=d.location("C", "Field"))
    wire = d.wiring(colour="BU", gauge="0.5")
    wire(x1.fn("x1")["2"], lamp.fn("lamp")["2"])
    wire(x1.fn("x1")["1"], plug.fn("x1")["1"])
    return fr.build(parts, d.draft(), system_document())


def _own_set_stubs(model) -> list[LinkMarker]:
    """The off stubs standing on pages of a unit's own drawing set."""
    pages, sets = layout_of(model, Page), layout_of(model, DrawingSet)
    return [
        m
        for m in layout_of(model, LinkMarker).values()
        if m.star is StarKind.OFF and sets[pages[m.page].drawing_set].unit is not None
    ]


def _far_unit(model, marker: LinkMarker):
    """The unit of the item the stub names."""
    assert marker.far is not None
    return items(model)[functions(model)[ports(model)[marker.far].function].item].unit


def test_no_stub_on_a_units_own_set_names_an_item_of_that_unit() -> None:
    """The wire `X1:2` - `L1:2` between a root pin and a child at another location is drawn, not
    stubbed; the wire to the top-level plug still ends in a stub that names the plug."""
    # UNDO: stages/offstubs.py `crosses_location`: drop `and a.drawing_set_key !=
    #     b.drawing_set_key` (the two top-level locations cross again: `+A-U2-X1:2` stubs)
    result = _build()
    model = result.model
    assert [f.code for f in result.findings if f.severity is Severity.ERROR] == []
    stubs = _own_set_stubs(model)
    assert stubs
    assert all(_far_unit(model, m) is None for m in stubs)
    texts = " ".join(marker_text(model, m) for m in stubs)
    assert "U2-X1" not in texts
    assert "U2-L1" not in texts
    assert "P1" in texts
