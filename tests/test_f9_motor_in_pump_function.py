"""F9 (layout deep dive, D10-D12): a field motor that belongs to a pump's function group `=P1`
sits outside the cabinet unit, at a top-level `+EXT`, in no unit and in no field group of its
own. It never un-owns `=P1` for the cabinet, so the cabinet's own set titles the page with the
group ("Pump 1", not the unit's name) and `own_nodes` keeps `=P1` and `+C1` and leaves `+EXT`
out; an off-stub names the far end by its product designation, "+EXT-M1:...", with no
function segment. A function node an item of another unit sits in is not the unit's own: the
relay board nested in the cabinet, in the cabinet's `=PLC`, keeps its short designation list
("-J1") and its unit-name page title (D15: a unit's own groups title its pages).

Can-fail, checked by hand: with `own_nodes` un-owning a function node for any outside item
(`if item not in members: outside.add(node_id)` for both aspects) the page-title tests and
the `own_nodes` test fail; with `_full_port` (folded into `end_text`, `stub_far_end`'s head
now, A3) reading `reference_designation` again the off-stub test failed.
"""

import re
from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import system_document

from fransys_model.derive import designation_list, unit_release
from fransys_model.derive.designation import own_nodes
from fransys_model.derive.drawing_text import off_stub_text, page_title
from fransys_model.kernel import Severity
from fransys_model.layout import DrawingSet, LinkMarker, Page, StarKind, layout_of
from fransys_model.vocab.tables import aspect_nodes, units

_PROJECT: dict[str, Any] = {
    "title": "Pump station",
    "number": "P-1001",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}

_STUB = re.compile(r"^-W\d+ [→←] \+EXT-\S+:.+")


def _laid_out(parts, draft):
    """`fr.build`'s model, after asserting it carries no `ERROR` (decision 0028: an `ERROR`
    stops `build` before layout, so the test would find no `layout.*` record to measure)."""
    result = fr.build(parts, draft, system_document())
    errors = [f.code for f in result.findings if f.severity is Severity.ERROR]
    assert errors == []
    return result.model


def _build():
    """A cabinet unit at +C1 whose strip terminal is wired by the top-level cable W1 to the
    motor M1 at the top-level +EXT. Both cabinet items and the motor sit in the top-level
    group `=P1` ("Pump 1"); the motor has no field group of its own."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    p1 = d.group("P1", "Pump 1")
    ext = d.location("EXT", "Field")
    u = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = u.location("C1", "Pump cabinet")
    x2 = u.strip("X2", at=c1)
    terminals = [x2.terminal("DEMO-TB-2.5", group=p1) for _ in range(2)]
    u.item("DEMO-CONN-2P", tag="X1", at=c1, group=p1)
    for terminal in terminals:
        u.boundary(terminal)
    motor = d.item("DEMO-MOTOR-4KW", tag="M1", at=ext, group=p1)
    cable = d.cable("DEMO-CBL-4G1.5", tag="W1", length_mm=15000)
    cable.core(1, terminals[0].outer, motor["U"])
    u.unused(terminals[1])  # the spare terminal: declared, so no BOUNDARY_UNCONNECTED
    return _laid_out(parts, d.draft())


def _cabinet(model):
    (cabinet,) = units(model)
    return cabinet


def _cabinet_pages(model):
    sets = layout_of(model, DrawingSet)
    pages = [p for p in layout_of(model, Page).values() if sets[p.drawing_set].unit is not None]
    assert pages
    return pages


def _labels(model, nodes) -> set[str]:
    return {aspect_nodes(model)[node].label for node in nodes}


def test_the_cabinets_own_set_titles_the_pump_page_with_the_group_not_the_unit() -> None:
    """The motor is in no unit, so `=P1` stays the cabinet's own and titles its page "Pump 1".
    Can-fail, checked by hand: un-own a function node for any outside item in `own_nodes` and
    the title falls back to the unit's name."""
    model = _build()
    titles = {page_title(model, p) for p in _cabinet_pages(model)}
    assert "Pump 1" in titles
    assert unit_release(model, _cabinet(model)).name not in titles


def test_the_cabinet_owns_the_pump_function_and_its_location_but_not_the_field_one() -> None:
    """`=P1` and `+C1` are the cabinet's own; `+EXT` holds only the motor, so it is not.
    Can-fail, checked by hand: un-own a function node for any outside item in `own_nodes` and
    "P1" leaves the set."""
    model = _build()
    own = _labels(model, own_nodes(model, _cabinet(model)))
    assert {"P1", "C1"} <= own
    assert "EXT" not in own


def test_an_off_stub_names_the_far_end_by_its_product_designation() -> None:
    """The cabinet's terminal stub reads "-W1 ← +EXT-M1:U": the cable, then the far
    device's location and item, no "=" function segment. Can-fail, checked by hand: read
    `reference_designation` again in `_full_port` (now `stub_far_end`'s head, A3) and the "=P1"
    segment broke the match."""
    model = _build()
    sets, pages = layout_of(model, DrawingSet), layout_of(model, Page)
    texts = [
        off_stub_text(model, m)
        for m in layout_of(model, LinkMarker).values()
        if m.star is StarKind.OFF and sets[pages[m.page].drawing_set].unit is not None
    ]
    assert texts
    for text in texts:
        assert _STUB.match(text), text
        assert "=" not in text


def test_a_function_node_shared_with_another_units_item_is_not_the_units_own() -> None:
    """Two cabinets at +C1 and +C2 each put an item in the top-level group `=P1`: each unit's
    item is at `=P1`, and so is an item of another unit, so neither owns it, while each still
    owns its own location. Can-fail, checked by hand: let an item of another unit leave a
    function node owned (drop `elif all_items[item].unit is not None` in `own_nodes`) and
    both units own "P1"."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    p1 = d.group("P1", "Pump 1")
    for name in ("cab1", "cab2"):
        u = d.scope(name).unit("demo-pump-cabinet", revision=1, interface="1")
        u.revision(1, date="2026-01-01", text="First release", created="XX")
        u.item("DEMO-CONN-2P", tag="X1", at=u.location(name.upper(), "Cabinet"), group=p1)
    model = fr.build(parts, d.draft(), system_document()).model
    assert len(units(model)) == 2
    owned = [_labels(model, own_nodes(model, unit)) for unit in units(model)]
    assert sorted(owned, key=sorted) == [{"CAB1"}, {"CAB2"}]  # no "P1", each its own location


def _build_nested_board():
    """A cabinet unit whose relay board is a unit nested in it; both stand in the top-level
    group `=PLC`, so `=PLC` holds items of two units."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    plc = d.group("PLC", "WAGO PLC")
    cab = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    cab.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = cab.location("C1", "Pump cabinet")
    cab.item("DEMO-CONN-2P", tag="X1", at=c1, group=plc)
    board = cab.scope("a2", at=c1, group=plc).unit("demo-io-board", revision=1, interface="1")
    board.revision(1, date="2026-01-01", text="First release", created="XX")
    pcb = board.item("DEMO-PCB-IO", name="board")
    j1 = board.item("DEMO-CONN-2P", tag="J1", parent=pcb)
    k1 = board.item("DEMO-RLY-2CO-24", name="k1", parent=pcb)
    wire = board.wiring(colour="BU", gauge="0.5")
    wire(j1["1"], k1.fn("coil")["A1"])
    wire(j1["2"], k1.fn("coil")["A2"])
    board.boundary(j1)
    board.unused(j1)  # nothing crosses the board's boundary: declared, so no BOUNDARY_UNCONNECTED
    return _laid_out(parts, d.draft())


def test_a_nested_board_keeps_its_short_list_and_its_unit_name_title() -> None:
    """The board's items stand in the cabinet's `=PLC`, so `=PLC` is not the board's own: its
    designation list prints "-J1" with no "=PLC" and its pages are titled with the unit's
    name, not "WAGO PLC". Can-fail, checked by hand: never un-own a function node in
    `own_nodes` (drop the `elif all_items[item].unit is not None` branch) and the list prints
    "=PLC-J1" and the pages read "WAGO PLC"."""
    model = _build_nested_board()
    board = next(u for u in units(model) if unit_release(model, u).name == "demo-io-board")
    references = {row.reference for row in designation_list(model, unit=board)}
    assert references
    assert not any("=" in reference for reference in references)
    assert "-J1" in references
    sets = layout_of(model, DrawingSet)
    pages = [p for p in layout_of(model, Page).values() if sets[p.drawing_set].unit == board]
    assert pages
    assert {page_title(model, p) for p in pages} == {"demo-io-board"}
