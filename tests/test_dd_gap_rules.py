"""F5-C gap tests (layout deep dive): D1 (a cyclic ring of poles), D4 (room for the first and last
rows' texts inside the content box) and D9 (junction dot and stub of a wired reference), built
through the `fransys` facade from `examples/demo-parts` and read from the laid-out
`layout.*` records, `Finding` codes and the rendered SVG only.

Box model of the D4 tests: a symbol's library keep-out, a label box (`x`, `y` top-left, one
`text_height` per line), and a link marker's box one wiring grid beyond its port (above an N port,
below an S port). A coil's A1 faces N and its A2 faces S; the marker record stores the port.
"""

import re
from collections import defaultdict
from itertools import pairwise
from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from _model_build_cover import layout_trigger_document
from fransys_render import pages as render_pages

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.geometry import WIRING_GRID, Orientation, symbol_geometry
from fransys_layout.lint.codes import LABEL_UNPLACED
from fransys_model.derive.drawing_text import (
    frame_column,
    frame_row,
    label_text,
    marker_text,
    off_stub_text,
    reference_number,
)
from fransys_model.kernel import Severity
from fransys_model.layout import (
    Label,
    LinkMarker,
    Page,
    Route,
    StarKind,
    SymbolPlacement,
    default_profile,
    default_sheet_format,
    layout_of,
)
from fransys_model.vocab.tables import functions, ports

_PROJECT: dict[str, Any] = {
    "title": "Gap rules",
    "number": "P-1005",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}
_MCB = "DEMO-MCB-C6"
_RELAY = "DEMO-RLY-2CO-24"
_LAMP = "DEMO-LAMP-24"


def _design():
    parts = fransys_parts.load("demo_parts")
    design = fransys_author.Design(parts)
    design.project(**_PROJECT)
    design.revision(1, date="2026-09-24", text="First issue", created="XX")
    return parts, design, design.location("C1", "Cabinet"), design.group("G1", "Group")


def _coil(model, name):
    """The placements of the coil of the item authored as `name`."""
    ids = {f.id for f in functions(model).values() if f.key[0] == name and f.name == "coil"}
    return [p for p in layout_of(model, SymbolPlacement).values() if p.function in ids]


# -- D1: a cyclic ring of poles ------------------------------------------------------------


def _ring(part: str, function: str, count: int):
    """`count` two-port devices h1..hN, each one's port 2 wired to the next one's port 1, the
    last back to the first: every net has exactly two ports."""
    parts, d, c1, grp = _design()
    wire = d.wiring(colour="BU", gauge="0.5")
    ring = [d.item(part, tag=f"H{n}", name=f"h{n}", at=c1, group=grp) for n in range(1, count + 1)]
    for at, one in enumerate(ring):
        wire(one.fn(function)["2"], ring[(at + 1) % count].fn(function)["1"])
    return fr.build(parts, d.draft(), layout_trigger_document())


@pytest.mark.parametrize("count", [3, 4])
def test_a_ring_of_poles_ends_where_it_closes_and_places_each_function_once(count) -> None:
    """D1: chain discovery over a ring of poles terminates; each function has one place, and the
    ring closes with a reference pair (M12)."""
    # UNDO: fransys_layout/stages/chains.py:discover_chains, drop the ring-termination guard
    #     `pole_of_port[q] not in visited` (backward walk) or `while cur not in walked` (forward).
    #     It fails only by HANGING (an endless walk); there is no pytest-timeout here, so a probe
    #     needs `timeout 60`. Dropping `seen.update(walked)` does NOT fail it: the duplicate chains
    #     are skipped because their functions are already placed.
    result = _ring(_MCB, "element", count)
    model = result.model
    assert not [f for f in result.findings if f.severity is Severity.ERROR]
    placed = layout_of(model, SymbolPlacement).values()
    assert len(placed) == count
    assert len({p.function for p in placed}) == count  # each function has exactly one place
    assert len({(p.page, p.x, p.y) for p in placed}) == count
    assert len({p.x for p in placed}) == 1  # the broken ring is one column
    rows = sorted(p.y for p in placed)
    pitch = rows[1] - rows[0]
    assert pitch > 0
    assert all(b - a == pitch for a, b in pairwise(rows))
    # M12 (a link that turns back around a device becomes a reference pair): the net that
    # closes the ring is no wire spanning the column but a reference and a branch on its two
    # ports; the other `count - 1` nets are wires joining neighbouring rows
    y_of = {port: p.y for p in placed for port in _ports_of(model, p.function)}
    routes = list(layout_of(model, Route).values())
    spans = [abs(y_of[route.a] - y_of[route.b]) // pitch for route in routes]
    assert spans == [1] * (count - 1)
    markers = list(layout_of(model, LinkMarker).values())
    (reference,) = (m for m in markers if m.star is StarKind.REF)
    (branch,) = (m for m in markers if m.star is StarKind.BRANCH)
    assert len(markers) == 2
    assert branch.partner == reference.id != branch.id  # the branch names the reference
    assert {reference.port, branch.port} not in [{r.a, r.b} for r in routes]  # the pair is no wire


def _ports_of(model, function):
    return [p.id for p in ports(model).values() if p.function == function]


@pytest.mark.parametrize("count", [3, 4])
def test_a_ring_of_generic_boxes_lays_out_and_places_each_function_once(count) -> None:
    """D1/D2: a ring of one-element chains (boxes have no through path) must not crash the run."""
    # UNDO: stages/attach.py:hub_order, rekey the column as `(*branches[0], "hub")`
    #     (drop `*column.key`): two hubs of a ring share a lowest branch, and the run raises
    #     LayoutError 'two columns carry one authoring key'
    model = _ring(_LAMP, "lamp", count).model
    placed = list(layout_of(model, SymbolPlacement).values())
    assert len({p.function for p in placed}) == len(placed) == count
    assert len({(p.page, p.x) for p in placed}) == count  # each box stands in a column of its own


# -- D4: room for the first and last rows' texts inside the content box --------------------


def _boxes(model):
    """Page id -> [(top, bottom)] of every keep-out, label box and marker box on that page."""
    height = default_profile().text_height
    placed = layout_of(model, SymbolPlacement)
    origin = {p.function: p for p in placed.values()}
    found = defaultdict(list)
    for p in placed.values():
        if p.symbol != "generic-box":
            keep = symbol_geometry(
                p.symbol, poles=p.poles, orientation=Orientation(p.orientation.value)
            ).keepout
            found[p.page].append((p.y + keep.y, p.y + keep.y + keep.height))
    for label in layout_of(model, Label).values():
        lines = label_text(model, label).count("\n") + 1
        found[label.page].append((label.y, label.y + lines * height))
    for marker in layout_of(model, LinkMarker).values():
        function = ports(model)[marker.port].function
        reach = WIRING_GRID + marker.stub_extra + marker.height  # stub, tier and box
        if marker.y <= origin[function].y:  # an N port: the box stands above the stub
            found[marker.page].append((marker.y - reach, marker.y))
        else:
            found[marker.page].append((marker.y, marker.y + reach))
    return found


def _content_height() -> int:
    sheet = default_sheet_format()
    return round(sheet.content_height_mm * 8 / float(sheet.module_mm))


def _star(*wires):
    """Relays K1..K4 whose coil pins the `wires` join, each end a pin spec "K1.A2" ("A1" faces N,
    "A2" faces S). The pins are mixed: M12 joins same-side pins by wires, so a star needs both."""
    parts, d, c1, grp = _design()
    wire = d.wiring(colour="BU", gauge="0.5")
    relays = {
        tag: d.item(_RELAY, tag=tag, name=tag.lower(), at=c1, group=grp).fn("coil")
        for tag in ("K1", "K2", "K3", "K4")
    }
    for first, second in wires:
        wire(*(relays[spec[:2]][spec[3:]] for spec in (first, second)))
    return fr.build(parts, d.draft(), layout_trigger_document()).model


def test_the_first_row_keeps_room_above_for_its_markers_inside_the_content_box() -> None:
    """D4, S20 M4: the hub's marker on the N port stands at or below the content-box top, and
    near it: the band along the top keeps the room for the turned box."""
    # UNDO: fransys_layout/stages/place.py `reference_band`: `return 0` (no band: the first
    #     row starts at the top and the marker box stands above the content box)
    model = _star(("K1.A1", "K2.A2"), ("K1.A1", "K3.A2"), ("K1.A1", "K4.A2"))
    markers = list(layout_of(model, LinkMarker).values())
    assert len(markers) == 4
    top = min(t for boxes in _boxes(model).values() for t, _ in boxes)
    assert top >= 0  # nothing stands above the content box
    assert top <= 8 * WIRING_GRID  # and the first row still starts near it (not vacuous)
    north = [m for m in markers if ports(model)[m.port].name == "A1"]
    assert len(north) == 1  # the hub's A1 faces N
    assert min(m.y - WIRING_GRID - m.stub_extra - m.height for m in north) == top  # topmost box


def test_the_last_row_keeps_room_below_for_its_markers_inside_the_content_box() -> None:
    """D4: markers on the S ports of the last row of a tall column end inside the content box."""
    # UNDO: fransys_layout/stages/place.py:_space
    #     `_space(page, profile.row_spacing)` becomes `_space(page, 400)` (rows then run past the
    #     content-box bottom). The `sink` term of `_text_room` (room below the last row) is NOT
    #     pinned: `sink = 0` still passes, the fixture stands too far from the page foot.
    parts, d, c1, grp = _design()
    wire = d.wiring(colour="BU", gauge="0.5")
    column = [d.item(_MCB, tag=f"Q{n}", at=c1, group=grp).fn("element") for n in (1, 2)]
    column += [d.item(_RELAY, tag=f"K{n}", at=c1, group=grp).fn("coil") for n in (1, 2, 3)]
    for above, below in pairwise(column):
        wire(
            above["2" if above in column[:2] else "A2"], below["1" if below in column[:2] else "A1"]
        )
    for n in range(3):
        wire(column[-1]["A2"], d.item(_RELAY, tag=f"X{n}", at=c1, group=grp).fn("coil")["A2"])
    result = fr.build(parts, d.draft(), layout_trigger_document())
    model = result.model
    assert "PAGE_OVERFULL" not in {f.code for f in result.findings}
    lowest = max(layout_of(model, LinkMarker).values(), key=lambda m: m.y)
    (k3,) = _coil(model, "K3")
    assert (lowest.page, lowest.y) == (
        k3.page,
        k3.y + 3 * WIRING_GRID,
    )  # a marker under the last row
    bottom = max(b for _, b in _boxes(model)[lowest.page])
    assert bottom >= lowest.y + WIRING_GRID + lowest.height  # the marker box is counted
    assert bottom <= _content_height()


# -- D9: junction dot and stub of a wired reference ----------------------------------------


def _grid(sheet, mm_x, mm_y):
    module = float(sheet.module_mm)
    return (
        round((float(mm_x) - sheet.content_x_mm) * 8 / module),
        round((float(mm_y) - sheet.content_y_mm) * 8 / module),
    )


def test_a_reference_wired_to_a_member_leaves_its_list_by_a_junction_dot_and_an_east_stub() -> None:
    """D9, S20 M7: hub K1.A1 is wired to K2.A1 and lists K3.A2 in a marker: dot one grid out, a
    stub E to the box's centre line (the fewest whole grids), then the vertical box. K3 stands on
    A2 so the net is a star: M12 would wire a same-side pair at any column distance."""
    # UNDO: stages/texts/marker_row.py, `_turns`: `return False` (the reference stays on its
    #     wire: no via, no dot, no E stub)
    parts, d, c1, grp = _design()
    wire = d.wiring(colour="BU", gauge="0.5")
    coil = {
        tag: d.item(_RELAY, tag=tag, name=tag.lower(), at=c1, group=grp).fn("coil")
        for tag in ("K1", "K2", "K3")
    }
    wire(coil["K1"]["A1"], coil["K2"]["A1"])
    wire(coil["K1"]["A1"], coil["K3"]["A2"])
    model = fr.build(parts, d.draft(), layout_trigger_document()).model
    (page,) = layout_of(model, Page).values()
    markers = list(layout_of(model, LinkMarker).values())
    (reference,) = (m for m in markers if m.star is StarKind.REF)
    assert len(markers) == 2  # the reference lists K3; K3's own marker names the reference
    (wired,) = (r for r in layout_of(model, Route).values() if reference.port in {r.a, r.b})
    points = [(p.x, p.y) for p in wired.points]
    assert points[0] == (reference.x, reference.y) or points[-1] == (reference.x, reference.y)
    if points[-1] == (reference.x, reference.y):
        points.reverse()
    (px, py), (nx, ny) = points[0], points[1]
    dx, dy = (nx > px) - (nx < px), (ny > py) - (ny < py)
    dot = (px + dx * WIRING_GRID, py + dy * WIRING_GRID)  # one grid out along the wire
    sheet = default_sheet_format()
    svg = render_pages(model)[f"{page.id.kind}:{page.id.value}"]
    dots = {
        _grid(sheet, x, y)
        for x, y in re.findall(r'<circle class="junction" cx="([^"]+)" cy="([^"]+)"', svg)
    }
    stubs = {
        (_grid(sheet, x1, y1), _grid(sheet, x2, y2))
        for x1, y1, x2, y2 in re.findall(
            r'<line class="marker" x1="([^"]+)" y1="([^"]+)" x2="([^"]+)" y2="([^"]+)"', svg
        )
    }
    assert dot in dots
    assert reference.via_x is not None
    assert (reference.via_x, reference.via_y) == dot  # the junction is the marker's via
    assert reference.box_x is not None
    end = (reference.box_x + reference.width // 2, dot[1])  # the box's centre line (M7)
    assert end[0] - dot[0] >= WIRING_GRID  # east of the dot by at least one grid
    assert (end[0] - dot[0]) % WIRING_GRID == 0  # and by whole grids
    assert (dot, end) in stubs


def _terminal_hub(*, far: tuple[str, ...] = ()):
    """A strip terminal X1 (model port `external`) wired to relays K4, K5, K6 in one location: a net
    of four with one terminal point, so X1 is the reference. K6 is wired on its A2 (south) pin,
    K4 and K5 on A1: M12 joins same-side pins by wires at any column distance, so a net of all-A1
    pins has no star. Each tag in `far` is a relay in another location wired to X1's `external`
    too. Returns the build result."""
    parts, d, c1, grp = _design()
    wire = d.wiring(colour="BU", gauge="0.5")
    x1 = d.item("DEMO-TB-2.5", tag="X1", at=c1, group=grp)
    for tag, pin in (("K4", "A1"), ("K5", "A1"), ("K6", "A2")):
        wire(x1["external"], d.item(_RELAY, tag=tag, at=c1, group=grp).fn("coil")[pin])
    fld = d.location("FLD", "Field")
    for tag in far:
        wire(x1["external"], d.item(_RELAY, tag=tag, at=fld, group=grp).fn("coil")["A1"])
    return fr.build(parts, d.draft(), layout_trigger_document())


def _stands_apart_from_the_wires(result, reference: LinkMarker) -> None:
    """The reference stands (a positive check) at the symbol port no wire of the page ends on,
    and nothing is left unplaced."""
    model = result.model
    ends = {
        (p.x, p.y)
        for route in layout_of(model, Route).values()
        if route.page == reference.page
        for p in (route.points[0], route.points[-1])
    }
    assert ends, "the page draws no wire to the terminal"
    assert (reference.x, reference.y) not in ends
    assert LABEL_UNPLACED not in {f.code for f in result.findings}


def _x1_markers(model) -> list[LinkMarker]:
    """Every marker on X1's `external` port: its reference, its stubs."""
    return [
        m
        for m in layout_of(model, LinkMarker).values()
        if ports(model)[m.port].name == "external"
        and functions(model)[ports(model)[m.port].function].key[0] == "X1"
    ]


def _x1_reference(model) -> LinkMarker:
    """The marker on X1's `external` port that lists the branches, merged with a stub or not
    (D9 F7): the `partner` every branch marker points at, `star` `REF` alone or `OFF` when
    merged with a stub -- read from the persisted link, not guessed from the now-symmetric
    text (LD3 (d))."""
    markers = layout_of(model, LinkMarker)
    x1_ids = {m.id for m in _x1_markers(model)}
    (reference,) = {
        markers[m.partner]
        for m in markers.values()
        if m.star is StarKind.BRANCH and m.partner in x1_ids
    }
    return reference


def test_a_terminal_reference_on_its_unwired_side_needs_no_turn() -> None:
    """layout-0053: X1's wires end at one symbol port, its reference stands at the other one (C22,
    `_free_side`): nothing crosses it, so it keeps its stub and draws no via (S20 M7 turns
    a reference only where a wire ends)."""
    # UNDO: stages/texts/marker_row.py, `_turns`, the turn's condition
    #     `(marker.drawing_set, marker.page, at.x, at.y) in room.wired_at` -> `True`: the
    #     reference turns although no wire ends on its symbol port
    result = _terminal_hub()
    reference = _x1_reference(result.model)
    assert reference.star is StarKind.REF
    assert reference.via_x is None
    assert reference.via_y is None
    _stands_apart_from_the_wires(result, reference)


def test_a_terminal_reference_with_an_off_stub_on_its_unwired_side_needs_no_turn() -> None:
    """layout-0053: the merged reference (a stub to another location in its last line) takes the
    same path: still on the unwired side, no via."""
    # UNDO: as above
    result = _terminal_hub(far=("K1",))
    reference = _x1_reference(result.model)
    assert reference.star is StarKind.OFF  # one record: the list and the stub
    assert reference.via_x is None
    _stands_apart_from_the_wires(result, reference)


def test_two_far_ends_on_a_reference_port_are_each_named_and_the_list_stays_apart() -> None:
    """layout-0053/0057: X1 lists K4-K6 and is wired to K1 and K2 in another location. One record
    cannot name two far ends, so the reference keeps its list alone and each far end has a stub
    (the two stubs share one box, S20 M3)."""
    # UNDO: schematic/write/markers.py: link_markers, a reference with two far ends merges the
    #     last one into its own record: the stubs merge into the reference and K1 is named nowhere
    result = _terminal_hub(far=("K1", "K2"))
    model = result.model
    reference = _x1_reference(model)
    assert reference.star is StarKind.REF
    _stands_apart_from_the_wires(result, reference)
    # the list, no stub line. The columns are derived from where the branch markers stand, not
    # pinned: they moved between 2/3 and 2/4 as the top-level tags shrank (D12, layout-0066) and the
    # image lane width changed (D7, layout-0064). One `#n-[p<page>:]<col><row>` line per branch
    # marker (LD3; the page only when another page than the reference's, model-0136), the marker's
    # own position on the house sheet, sorted as `marker_text` sorts them.
    sheet = default_sheet_format()
    content_width = round(sheet.content_width_mm * 8 / float(sheet.module_mm))
    content_height = round(sheet.content_height_mm * 8 / float(sheet.module_mm))
    pages = layout_of(model, Page)
    branches = [
        m
        for m in layout_of(model, LinkMarker).values()
        if m.partner == reference.id and m.star is StarKind.BRANCH
    ]
    assert branches
    number = reference_number(model, reference)
    expected = sorted(
        ("" if m.page == reference.page else f"p{pages[m.page].number}:")
        + f"{frame_column(content_width, sheet.frame_columns, m.x)}"
        f"{frame_row(content_height, sheet.frame_rows, m.y)}"
        for m in branches
    )
    assert marker_text(model, reference) == "\n".join(
        f"#{number}-{position}" for position in expected
    )
    stubs = [m for m in _x1_markers(model) if m.star is StarKind.OFF]
    assert len({m.id for m in _x1_markers(model)}) == 3  # the list and one stub per far end
    texts = sorted(off_stub_text(model, m) for m in stubs)
    assert len(texts) == 2
    assert texts[0].endswith("+FLD-K1:A1")
    assert texts[1].endswith("+FLD-K2:A1")


def test_a_turned_reference_with_an_off_stub_renders_and_prints_the_measured_arrow() -> None:
    """D9 (F7 merge, layout-0053): a reference that is wired AND carries a stub to another location
    turns E and stays one off-stub record; render draws it and prints the arrow layout measured."""
    # UNDO: fransys_render/_markers.py:_turned_glyphs, drop `far=None, carrier=None,
    #     facing=None` from its `dataclasses.replace(...)`: render raises SchemaError
    # UNDO: fransys_layout/engines/schematic/write/markers.py:_facing, delete the
    #     `if one.turn is not None:` branch: the turned stub reads E and prints "->" where
    #     layout measured "<-"
    parts, d, c1, grp = _design()
    hub = d.item("DEMO-CONN-2P", tag="J1", name="j1", at=c1, group=grp)["1"]
    wire = d.wiring(colour="BU", gauge="0.5")
    for tag in ("H1", "H2"):
        wire(hub, d.item(_LAMP, tag=tag, name=tag.lower(), at=c1, group=grp).fn("lamp")["1"])
    far = d.item("DEMO-CONN-2P", tag="Q1", at=d.location("FLD", "Field"), group=grp)["1"]
    d.cable("DEMO-CBL-4G1.5", tag="W1").core(1, hub, far)
    model = fr.build(parts, d.draft(), layout_trigger_document()).model
    pages = render_pages(model)  # raises when the turned merged marker cannot be drawn
    (merged,) = (m for m in layout_of(model, LinkMarker).values() if m.via_x is not None)
    assert merged.star is StarKind.OFF  # one record: the list and the stub
    svg = pages[f"{merged.page.kind}:{merged.page.value}"]
    results, _ = stage_results(model, read_inputs(model))
    (measured,) = (m.text for m in results.layout.markers if m.text and m.port == merged.port)
    assert marker_text(model, merged).split("\n")[-1] == measured
    assert measured in svg


def test_a_turned_reference_that_carries_a_stub_is_one_merged_record_render_draws() -> None:
    """S20 M7 with D9's F7 merge: a reference where a wire ends turns, and when it also carries a
    stub to another location it stays one off-stub record (a via, the list's line and the stub's
    line in one box); render draws it and prints the arrow layout measured. K1.A1 is wired to
    K2.A1, K4.A1 and K3.A2 (a star: M12 wires same-side pins), and a cable core leaves it for
    +FLD."""
    # UNDO: fransys_render/_markers.py:_turned_glyphs, drop `far=None, carrier=None,
    #     facing=None` from its `dataclasses.replace(...)`: render raises SchemaError
    parts, d, c1, grp = _design()
    wire = d.wiring(colour="BU", gauge="0.5")
    relays = {
        tag: d.item(_RELAY, tag=tag, name=tag.lower(), at=c1, group=grp).fn("coil")
        for tag in ("K1", "K2", "K3", "K4")
    }
    hub = relays["K1"]["A1"]
    for other in (relays["K2"]["A1"], relays["K3"]["A2"], relays["K4"]["A1"]):
        wire(hub, other)
    far = d.item("DEMO-CONN-2P", tag="Q1", at=d.location("FLD", "Field"), group=grp)["1"]
    d.cable("DEMO-CBL-4G1.5", tag="W1").core(1, hub, far)
    model = fr.build(parts, d.draft(), layout_trigger_document()).model
    pages = render_pages(model)  # raises when the turned merged marker cannot be drawn
    (merged,) = (m for m in layout_of(model, LinkMarker).values() if m.via_x is not None)
    assert merged.star is StarKind.OFF  # one record: the list and the stub
    assert merged.port == hub.id
    svg = pages[f"{merged.page.kind}:{merged.page.value}"]
    results, _ = stage_results(model, read_inputs(model))
    (measured,) = (m.text for m in results.layout.markers if m.text and m.port == merged.port)
    assert marker_text(model, merged).split("\n")[-1] == measured
    assert measured in svg
