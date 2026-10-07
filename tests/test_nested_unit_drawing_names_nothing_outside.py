"""A nested unit's own drawing names nothing outside it (unit documents U2, deep-dive D10;
owner rule 2026-09-24).

The units worked example's nested board (`demo-io-board`, prefix `pump1`) sits in the
cabinet (`demo-pump-cabinet`, prefix `pump1`), which sits at `+ER+C1` beside a harness
`-WH1` and field wiring to `+FLD`. The board's own pages end at the boundary pin (`-X1:1`):
no stub label, no marker, no text naming the harness, a location or the cabinet. The
cabinet's page draws the boundary at the black box: the board's `-X1` inside the outline,
the harness plug `-WH1-P1` outside it on the mating line.

The collector reads the same drawing text the renderer prints: `label_text`, `marker_text`,
`page_title` and `outline_title`. The cabinet, a top-level unit, is the can-fail contrast:
the same collector finds the `+FLD` stub names on its set.
"""

import sys
from pathlib import Path
from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import layout_trigger_document

# `test_declared_dependencies.py`'s pattern for importing a sibling root test module.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_units_worked_example import _system_design
from test_write_unit_worked_example import _unit_id

from fransys_layout.engines.schematic import lay_out_schematic
from fransys_model.derive.drawing_text import (
    label_text,
    marker_text,
    outline_title,
    page_title,
)
from fransys_model.kernel import Severity
from fransys_model.layout import (
    DrawingSet,
    Label,
    LinkMarker,
    Outline,
    Page,
    StarKind,
    SymbolPlacement,
    layout_of,
)
from fransys_model.vocab.tables import functions, items, mates

# Everything in the worked example that stands outside the board: the harness `-WH1` and its
# plug `-WH1-P1`, the location paths `+ER+C1` and `+FLD`, the cabinet's scope `pump1`, the
# motor `-M1`, and the `+` and `=` that start a location or function path. None of them is a
# substring of a board-inside text (`-K1`, `-X1:1`, `A1`, contact numbers, `/1.1`, "I/O board").
_OUTSIDE = ("WH1", "P1", "+", "=", "ER", "C1", "FLD", "pump", "M1")


def _model_and_units():
    parts = fransys_parts.load("demo_parts")
    design, _field1, _field2 = _system_design(parts)
    model = fr.build(parts, design.draft(), layout_trigger_document()).model
    cabinet = _unit_id(model, name="demo-pump-cabinet", prefix="pump1")
    board = _unit_id(model, name="demo-io-board", prefix="pump1")
    return model, cabinet, board


_MODEL, _CABINET, _BOARD = _model_and_units()


def _pages_of(model, unit):
    sets = layout_of(model, DrawingSet)
    return [p for p in layout_of(model, Page).values() if sets[p.drawing_set].unit == unit]


def _texts(model, pages):
    """Every text `pages` print: labels, markers, page titles and outline titles."""
    page_ids = {p.id for p in pages}
    texts = [page_title(model, p) for p in pages]
    texts += [
        label_text(model, lb) for lb in layout_of(model, Label).values() if lb.page in page_ids
    ]
    texts += [
        marker_text(model, m) for m in layout_of(model, LinkMarker).values() if m.page in page_ids
    ]
    texts += [
        outline_title(model, o.unit)
        for o in layout_of(model, Outline).values()
        if o.page in page_ids
    ]
    return texts


def _outside_hits(texts):
    return {(token, text) for text in texts for token in _OUTSIDE if token in text}


def test_the_boards_own_pages_name_nothing_outside_and_end_at_the_boundary_pin() -> None:
    """U2/D10: no text of the board's pages names anything outside it; the pins print `-X1:n`."""
    # UNDO: give the board's set a `star=off` stub (`_texts` gains "-WH1 -> +ER+C1-X1:1") and
    #   the hit set is no longer empty
    pages = _pages_of(_MODEL, _BOARD)
    assert pages  # positive half: the board has a set of its own
    texts = _texts(_MODEL, pages)
    assert {"-X1:1", "-X1:2"} <= set(texts)  # the page ends at the boundary pin
    assert "-K1" in texts  # and holds the board's own content
    page_ids = {p.id for p in pages}
    assert not [m for m in layout_of(_MODEL, LinkMarker).values() if m.page in page_ids]
    assert _outside_hits(texts) == set()


def test_the_cabinets_own_set_does_name_outside_things_so_the_collector_can_fail() -> None:
    """The contrast: the top-level cabinet keeps its `+FLD` stubs, the collector finds them."""
    # UNDO: none needed, this test is the can-fail proof of the collector itself
    texts = _texts(_MODEL, _pages_of(_MODEL, _CABINET))
    hit_tokens = {token for token, _text in _outside_hits(texts)}
    assert {"+", "FLD", "M1"} <= hit_tokens
    assert any("+FLD-M1:U" in text for text in texts)


def test_the_cabinets_page_draws_the_boards_boundary_pin_mated_to_the_harness_plug() -> None:
    """U2/D10: on the cabinet's page the board's `-X1` is a black box inside the board's
    outline, and the harness plug it mates stands outside on the mating line, pin over pin.
    A mate has no route: it is the adjacency of the plug and the boundary pins."""
    # UNDO: layout stops replicating the boundary function on the parent's page (no black-box
    #   placement) and `boundary` below is empty
    model = _MODEL
    cabinet_pages = {p.id for p in _pages_of(model, _CABINET)}
    (outline,) = [
        o
        for o in layout_of(model, Outline).values()
        if o.unit == _BOARD and o.page in cabinet_pages
    ]
    on_page = [p for p in layout_of(model, SymbolPlacement).values() if p.page == outline.page]
    boundary = [
        p for p in on_page if items(model)[functions(model)[p.function].item].unit == _BOARD
    ]
    assert boundary
    assert {functions(model)[p.function].key[-3:-1] for p in boundary} == {("X1", "fn")}
    for p in boundary:
        assert outline.x <= p.x <= outline.x + outline.width
        assert outline.y < p.y <= outline.y + outline.height
    (mate,) = [m for m in mates(model).values() if {m.a, m.b} & {p.function for p in boundary}]
    plug_functions = {mate.a, mate.b} - {p.function for p in boundary}
    plug = [p for p in on_page if p.function in plug_functions]
    assert plug
    assert {p.x for p in plug} == {p.x for p in boundary}  # pin over pin
    # the plug is outside the outline, on the mating line's other side
    assert all(not outline.y <= p.y <= outline.y + outline.height for p in plug)


_PROJECT: dict[str, Any] = {
    "title": "Pump station",
    "number": "P-1001",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _build_boundary_mated_to_top_level_harness(*, nested: bool):
    """`tests/test_unit_boundary_off_stub.py::_build`, with the unit whose boundary X1 mates the
    +C1 plug of the top-level harness W3 (running to +FLD) either top level or nested in an
    outer unit. Returns the model and the id of that unit."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    if nested:
        outer = d.scope("outer").unit("demo-pump-cabinet", revision=1, interface="1")
        outer.revision(1, date="2026-01-01", text="First release", created="XX")
        c1 = outer.location("C1", "Pump cabinet")
        u = outer.scope("cab", at=c1).unit("demo-io-board", revision=1, interface="1")
        u.revision(1, date="2026-01-01", text="First release", created="XX")
    else:
        u = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
        u.revision(1, date="2026-01-01", text="First release", created="XX")
        c1 = u.location("C1", "Pump cabinet")
    grp = u.group("NET", "Network")
    x1 = u.item("DEMO-CONN-2P", tag="X1", at=c1, group=grp)
    u.boundary(x1)
    fld, field = d.location("FLD", "Field"), d.group("NET", "Network")
    w3 = d.harness(name="w3", tag="W3", at=c1, group=field)
    p1 = d.item("DEMO-CONN-2P", tag="P1", parent=w3, at=c1, group=field)
    p2 = d.item("DEMO-CONN-2P", tag="P2", parent=w3, at=fld, group=field)
    cable = d.cable("DEMO-CBL-4G1.5", name="w3c", parent=w3, at=c1)
    cable.core(1, p1["1"], p2["1"])
    cable.core(2, p1["2"], p2["2"])
    d.mate(p1, x1)
    result = fr.build(parts, d.draft(), layout_trigger_document())
    model = result.model
    errors = {f.code for f in result.findings if f.severity is Severity.ERROR}
    if nested:
        # The mate bypasses the outer unit's boundary on purpose: `UNIT_BOUNDARY_BYPASSED` is an
        # ERROR, so `fr.build` runs no layout (decision 0028); lay the numbered model out directly.
        assert errors == {"UNIT_BOUNDARY_BYPASSED"}
        model, _findings = lay_out_schematic(model)
    else:
        assert errors == set()
    name = "demo-io-board" if nested else "demo-pump-cabinet"
    return model, _unit_id(model, name=name, prefix="outer" if nested else "cab")


def _own_set_stubs(model, unit):
    pages = {p.id for p in _pages_of(model, unit)}
    return [
        m
        for m in layout_of(model, LinkMarker).values()
        if m.page in pages and m.star is StarKind.OFF
    ]


def test_a_nested_units_boundary_pin_mated_to_a_top_level_harness_draws_no_stub() -> None:
    """D10/U2: the nested unit's own set ends at the pin: no off-stub for the mate's cable."""
    # UNDO: engine.py `_off_inputs`: `outward = black_box_sets(...)` becomes `outward = {}` (the
    #   stub "-W3 <- +FLD-P2:1 2" is drawn in the nested unit's own set)
    model, unit = _build_boundary_mated_to_top_level_harness(nested=True)
    pages = _pages_of(model, unit)
    assert pages  # positive half: the nested unit has a set of its own
    page_ids = {p.id for p in pages}
    x1_pins = [
        p
        for p in layout_of(model, SymbolPlacement).values()
        if p.page in page_ids and "X1" in functions(model)[p.function].key
    ]
    assert len(x1_pins) == 2  # X1's two pins are drawn there
    assert _own_set_stubs(model, unit) == []


def test_a_top_level_units_boundary_pin_keeps_the_stub_of_the_mated_cable() -> None:
    """D10: the top-level unit's own set keeps "-W3 <- +FLD..." (passes before and after)."""
    # UNDO: fransys_layout/engines/schematic/read/offstubs.py: `boundary_offs` skips every unit
    model, unit = _build_boundary_mated_to_top_level_harness(nested=False)
    stubs = _own_set_stubs(model, unit)
    assert stubs
    assert all(marker_text(model, m).startswith("-W3") for m in stubs)
    assert all("+FLD" in marker_text(model, m) for m in stubs)


def test_the_parent_page_draws_the_stub_of_a_top_level_cable_mated_at_a_nested_boundary_pin() -> (
    None
):
    """D10: for a nested unit the stub stands on the parent's page, at the black box's pin."""
    # UNDO: engine.py `_off_inputs`: `outward = black_box_sets(...)` becomes `outward = {}` (the
    #   stub falls back to the home placement, the nested unit's own set, and no stub stands on
    #   the parent's)
    model, unit = _build_boundary_mated_to_top_level_harness(nested=True)
    sets = layout_of(model, DrawingSet)
    pages = layout_of(model, Page)
    replica_sets = {
        pages[p.page].drawing_set
        for p in layout_of(model, SymbolPlacement).values()
        if items(model)[functions(model)[p.function].item].unit == unit
        and sets[pages[p.page].drawing_set].unit != unit
    }
    assert replica_sets  # positive half: the black-box replica of X1 stands in another set
    stubs = [
        m
        for m in layout_of(model, LinkMarker).values()
        if pages[m.page].drawing_set in replica_sets
        and m.star is StarKind.OFF
        and marker_text(model, m).startswith("-W3")
        and "+FLD" in marker_text(model, m)
    ]
    assert stubs
