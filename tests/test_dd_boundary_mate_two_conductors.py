"""EF-C Part 9: one conductor, one text. A unit's boundary pin mated outside its unit, whose
outside mate has two conductors leaving the location, shows two off stubs in the unit's own set,
each naming its own far end (layout-0057: the k-th end of a port takes the k-th text).

Built through the `fransys` facade from `examples/demo-parts`; read from `layout.*` records. The
stub tests carry the two conductors as single wires: two cores of one harness make a line (HL1),
which leaves in one stub per line (HL18, owner C1), so the per-conductor rule has no stub to read.
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from _model_build_cover import layout_trigger_document

from fransys_model.derive.drawing_text import off_stub_text
from fransys_model.layout import (
    CableBlock,
    CoreWire,
    DrawingSet,
    EndBox,
    LinkMarker,
    Page,
    StarKind,
    layout_of,
)

_PROJECT: dict[str, Any] = {
    "title": "Two conductors",
    "number": "P-1009",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _build(*, wires: bool = False):
    """A cabinet unit at +C1 whose boundary pin X1:1 mates the plug P1 of the top-level harness
    W3; the plug's pin 1 carries two cores, one to Q1 and one to R1, both at +FLD. With `wires`
    the two conductors are single wires and no harness: no line (HL1)."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    u = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = u.location("C1", "Pump cabinet")
    grp = u.group("NET", "Network")
    x1 = u.item("DEMO-CONN-2P", tag="X1", at=c1, group=grp)
    u.boundary(x1)
    fld, field = d.location("FLD", "Field"), d.group("NET", "Network")
    w3 = None if wires else d.harness(name="w3", tag="W3", at=c1, group=field)
    p1 = d.item("DEMO-CONN-2P", tag="P1", parent=w3, at=c1, group=field)
    q1 = d.item("DEMO-CONN-2P", tag="Q1", parent=w3, at=fld, group=field)
    r1 = d.item("DEMO-CONN-2P", tag="R1", parent=w3, at=fld, group=field)
    if wires:
        wire = d.wiring(colour="BU", gauge="0.5")
        wire(p1["1"], q1["1"])
        wire(p1["1"], r1["1"])
    else:
        cable = d.cable("DEMO-CBL-4G1.5", name="w3c", parent=w3, at=c1)
        cable.core(1, p1["1"], q1["1"])
        cable.core(2, p1["1"], r1["1"])
    d.mate(p1, x1)
    return fr.build(parts, d.draft(), layout_trigger_document()).model


def _unit_stubs(model):
    """The off stubs drawn in a unit's own drawing set."""
    sets = layout_of(model, DrawingSet)
    return [
        m
        for m in layout_of(model, LinkMarker).values()
        if m.star is StarKind.OFF and sets[layout_of(model, Page)[m.page].drawing_set].unit
    ]


def test_a_boundary_pin_whose_mate_has_two_conductors_shows_two_stubs_each_naming_its_own_end() -> (
    None
):
    """Two conductors leave the mate's location: two stubs on the unit's pin, "-> +FLD-Q1:1"
    and "-> +FLD-R1:1", not one stub naming the last far end."""
    # UNDO: engines/schematic/read/offstubs.py: the boundary pin's `texts` take
    #   `reads.end_text(leaving[-1], ...)` for every conductor (the last text per port; by probe)
    model = _build(wires=True)
    texts = sorted(off_stub_text(model, m) for m in _unit_stubs(model))
    assert len(texts) == 2, texts
    assert "Q1" in texts[0]
    assert "R1" in texts[1]


@pytest.mark.xfail(
    strict=True,
    reason=(
        "layout-0093 known limit (designer ruling (a), 2026-10-02): two OFF stubs of one carrier "
        "to one far end on stacked neighbouring S pins of one column should share one box, but "
        "the upper pin's stub runs into the lower pin's body, so no box stands clear of both "
        "(M9); the pair keeps two boxes and the first stands on the lower pin"
    ),
)
def test_two_stubs_of_one_carrier_to_one_far_end_on_stacked_pins_share_one_box() -> None:
    """On the plug's page the two stacked pins of the plug each stub "-> +C1-X1:1": the
    same carrier and far end, so one box, one position and size for both."""
    model = _build(wires=True)
    stubs = [
        m
        for m in layout_of(model, LinkMarker).values()
        if m.star is StarKind.OFF and off_stub_text(model, m).endswith("+C1-X1:1")
    ]
    assert len(stubs) == 2
    assert len({(m.page, m.x, m.y, m.width, m.height) for m in stubs}) == 1


def test_the_two_conductors_of_the_plug_pin_draw_as_a_cable_block() -> None:
    """CD-H7 at P1: W3's cable lands both cores on the plug's pin 1, so its block draws.

    The plug's end box is its pin 1, two places wide, and its free pin 2, one wide.
    """
    model = _build()
    (block,) = layout_of(model, CableBlock).values()
    ends = [e for e in layout_of(model, EndBox).values() if e.block == block.id]
    (plug,) = [e for e in ends if e.width == 3 * block.pitch]
    assert [cell.landed for cell in plug.pins] == [True, False]
    assert plug.pins[0].x == plug.x + block.pitch
    assert len(layout_of(model, CoreWire)) == 2
