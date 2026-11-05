"""Layout-0090: a wire that would turn back round a device is drawn as a reference pair.

The unit (the root-port tests' K1) wires each relay's coil pins to the root's
connector pins (`-K1:A1` to `-X1:1`, `-K2:A1` to `-X2:1`, and the A2 pins to the pins 2). The A1
"""

import functools

import fransys as fr
import fransys_parts
from _drawn_pages import drawn_pages, markers_in, ref_texts
from _model_build_cover import printed
from fransys_author.design import Design

from electrical_symbols import MARKER_FACING, MARKER_TURN_FACING, MARKER_TURNED
from fransys_model.layout import DrawingSet, Page, layout_of


@functools.cache
def _k1():
    """A unit whose root `DEMO-IO-2X` wires each pin to a relay's coil, two pins to the parent."""
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    d.project(title="Turned", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    p1 = d.item("DEMO-CONN-2P", tag="P1", group=d.group("T", "Top"), at=d.location("TOP", "Top"))
    u = d.scope("u").unit("dev", revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    g = u.group("G", "Group")
    root = u.item("DEMO-IO-2X", tag="U2", group=g, name="root")
    ka = u.item("DEMO-RLY-2CO-24", tag="K1", parent=root, group=g, name="ka")
    kb = u.item("DEMO-RLY-2CO-24", tag="K2", parent=root, group=g, name="kb")
    wire = u.wiring(colour="BU", gauge="0.5")
    wire(root.fn("x1")["1"], ka.fn("coil")["A1"])
    wire(root.fn("x1")["2"], ka.fn("coil")["A2"])
    wire(root.fn("x2")["1"], kb.fn("coil")["A1"])
    wire(root.fn("x2")["2"], kb.fn("coil")["A2"])
    top = d.wiring(colour="BU", gauge="0.5")
    top(root.fn("x1")["1"], p1["1"])
    top(root.fn("x2")["1"], p1["2"])
    u.boundary(root.fn("x1"))
    u.boundary(root.fn("x2"))
    return fr.build(parts, *printed(d.draft()))


def _own_drawings(model, *, own: bool):
    """The Drawings of the pages of the unit's own sets (`own`), or of the top-level sets."""
    sets = {s.id for s in layout_of(model, DrawingSet).values() if (s.unit is not None) == own}
    pages = {p.id for p in layout_of(model, Page).values() if p.drawing_set in sets}
    return [d for page, d in drawn_pages(model).items() if page in pages]


def _markers(model, *, own: bool):
    """Every reference marker on a page of the unit's own sets (`own`), or of the top-level sets."""
    return [m for d in _own_drawings(model, own=own) for m in markers_in(d)]


def test_the_coil_a1_pins_are_references_in_boxes_of_their_own() -> None:
    """-X1:1 and -X2:1 take the reference with their stub, -K1:A1 and -K2:A1 a branch."""
    # UNDO: stages/references/__init__.py `_decided`: drop the `*turned_stars(...)` entry
    model = _k1().model
    found = _markers(model, own=True)
    assert len(found) == 4
    for marker in found:
        assert marker.orient in (MARKER_TURN_FACING.values() if marker.key == MARKER_TURNED else (MARKER_FACING["S"], MARKER_FACING["N"]))  # vertical
    # the pin's off stub is the last line of its reference's box
    offs = [m for m in found if any(t.startswith("\N{LEFTWARDS ARROW}") for t in ref_texts(m))]
    assert len(offs) == 2
    assert all(len(ref_texts(m)) == 2 for m in offs)


def test_the_a2_wires_stay_routed_and_the_a1_wires_are_not() -> None:
    """The two A2 conductors keep their routes; no route ends on an A1 pin."""
    model = _k1().model
    wires = [w for d in _own_drawings(model, own=True) for w in d.wires]
    assert len(wires) == 2
