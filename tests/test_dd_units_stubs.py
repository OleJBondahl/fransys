"""F5-C undo tests for D10 (stub labels) and D11 (unit outlines), through the facade.

Every test reads public records only: `layout.*` records, the `drawing_text` readers and the
rendered SVG of `fransys_render.pages`; none reads `ext` or a private name. Each test
carries a `# UNDO:` line, the one mutation that must make it fail.

Fixtures: `test_unit_boundary_off_stub._build` (a cabinet unit whose boundary X1 mates the
plug P1 of the top-level harness W3 to +FLD), `test_units_worked_example._build_system` (two
pump cabinets and two board units), and `_build_two_connectors`, a cabinet unit with two
boundary connectors, each mated to its own top-level harness plug.
"""

import functools
import importlib.util
import re
from collections import defaultdict
from pathlib import Path

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from _model_build_cover import layout_trigger_document
from fransys_render import pages as render_pages

from fransys_layout.stages.tidy import TEXT_GAP
from fransys_model.derive import (
    connector_box_lines,
    draws_as_line,
    revision_text,
    unit_release,
)
from fransys_model.derive.designation import own_nodes
from fransys_model.derive.drawing_text import label_text, marker_text, stub_far_end
from fransys_model.layout import (
    ConnectorBox,
    DrawingSet,
    Label,
    LinkMarker,
    Outline,
    Page,
    StarKind,
    SymbolPlacement,
    default_profile,
    layout_of,
)
from fransys_model.vocab import Aspect
from fransys_model.vocab.tables import aspect_nodes, functions, units

_ARROWS = "←→"  # left and right arrow: the stub text's arrow, direction not pinned


def _load(name: str):
    """A sibling root test module, loaded by path (root tests are not a package)."""
    spec = importlib.util.spec_from_file_location(name[:-3], Path(__file__).with_name(name))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_OFF_STUB = _load("test_unit_boundary_off_stub.py")
_SYSTEM = _load("test_units_worked_example.py")


@functools.cache
def _off_stub_model():
    return _OFF_STUB._build().model


@functools.cache
def _system_model():
    return _SYSTEM._build_system()[0].model


def _build_two_connectors(*, relay_between: bool, lines: bool = True):
    """A cabinet unit `+C1` with boundary connectors X1 and X2, each mated to the plug of its
    own top-level harness. With `relay_between` the plugs stand in groups A and C and a top-level
    relay in group B, so a column that is none of the unit's stands between the two connectors.
    Without `lines` single wires stand for each harness: no line (HL1), so per-pin stubs and
    D11 frames."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_OFF_STUB._PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    u = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = u.location("C1", "Pump cabinet")
    grp = u.group("NET", "Network")
    connectors = [u.item("DEMO-CONN-2P", tag=f"X{n}", at=c1, group=grp) for n in (1, 2)]
    for connector in connectors:
        u.boundary(connector)
    fld = d.location("FLD", "Field")
    groups = [d.group(key, key) for key in ("A", "B", "C")]
    for n, connector in enumerate(connectors):
        group = groups[2 * n] if relay_between else groups[0]
        harness = d.harness(name=f"h{n}", tag=f"W{n + 3}", at=c1, group=group) if lines else None
        plug = d.item("DEMO-CONN-2P", tag=f"P{n + 1}", parent=harness, at=c1, group=group)
        far = d.item("DEMO-CONN-2P", tag=f"Q{n + 1}", parent=harness, at=fld, group=group)
        if lines:
            cable = d.cable("DEMO-CBL-4G1.5", name=f"c{n}", parent=harness, at=c1)
            cable.core(1, plug["1"], far["1"])
            cable.core(2, plug["2"], far["2"])
        else:
            wire = d.wiring(colour="BU", gauge="0.5")
            wire(plug["1"], far["1"])
            wire(plug["2"], far["2"])
        d.mate(plug, connector)
    if relay_between:
        relay = d.item("DEMO-RLY-2CO-24", tag="K1", at=c1, group=groups[1])
        wire = d.wiring(colour="BU", gauge="0.5")
        wire(relay.fn("coil")["A1"], relay.fn("coil")["A2"])
        wire(relay.fn("co_1")["11"], relay.fn("co_1")["14"])  # layout-0112: wired, so drawn
        wire(relay.fn("co_2")["21"], relay.fn("co_2")["24"])
    return fr.build(parts, d.draft(), layout_trigger_document()).model


def _two_location_cable_model():
    """A top-level cable W1 between plugs P1 at +A and P2 at +B, both in the function group G."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_OFF_STUB._PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    a, b = d.location("A", "Cabinet"), d.location("B", "Field")
    group = d.group("G", "Pump")
    p1 = d.item("DEMO-CONN-2P", tag="P1", at=a, group=group)
    p2 = d.item("DEMO-CONN-2P", tag="P2", at=b, group=group)
    cable = d.cable("DEMO-CBL-4G1.5", tag="W1")
    cable.core(1, p1["1"], p2["1"])
    cable.core(2, p1["2"], p2["2"])
    return fr.build(parts, d.draft(), layout_trigger_document()).model


def _two_location_wires_model():
    """`_two_location_cable_model` with two single wires for the cable: no line (HL1)."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_OFF_STUB._PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    a, b = d.location("A", "Cabinet"), d.location("B", "Field")
    group = d.group("G", "Pump")
    p1 = d.item("DEMO-CONN-2P", tag="P1", at=a, group=group)
    p2 = d.item("DEMO-CONN-2P", tag="P2", at=b, group=group)
    wire = d.wiring(colour="BU", gauge="0.5")
    wire(p1["1"], p2["1"])
    wire(p1["2"], p2["2"])
    return fr.build(parts, d.draft(), layout_trigger_document()).model


def _set_of(model, page_id):
    return layout_of(model, DrawingSet)[layout_of(model, Page)[page_id].drawing_set]


def _stubs(model, *, own_set: bool):
    """The stub-label markers (their text carries an arrow) in unit sets or in top-level sets."""
    return [
        m
        for m in layout_of(model, LinkMarker).values()
        if any(a in marker_text(model, m) for a in _ARROWS)
        and (_set_of(model, m.page).unit is not None) == own_set
    ]


def _normal(text: str) -> str:
    """The stub text with its arrow direction unified: the spec example and the branch differ."""
    return text.replace("←", "→")


def _svg_boxes_and_stubs(svg: str):
    """The marker boxes `(x0, y0, x1, y1)` and the stub line ends `(x, y)` of one page, in mm."""
    boxes = []
    for points in re.findall(r'<polyline class="marker" points="([^"]+)"', svg):
        pairs = [tuple(map(float, pair.split(","))) for pair in points.split()]
        xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
        boxes.append((min(xs), min(ys), max(xs), max(ys)))
    lines = re.findall(r'<line class="marker" x1="[^"]+" y1="[^"]+" x2="([^"]+)" y2="([^"]+)"', svg)
    return boxes, [(float(x), float(y)) for x, y in lines]


def _harness_line_ends(svg: str):
    """Each harness line's first and last point `(x, y)` of one page, in mm."""
    found = []
    for points in re.findall(r'<polyline class="harness-line" points="([^"]+)"', svg):
        pairs = [tuple(map(float, pair.split(","))) for pair in points.split()]
        found.extend((pairs[0], pairs[-1]))
    return found


def _on_box_edge(box, end) -> bool:
    x0, y0, x1, y1 = box
    x, y = end
    return x0 <= x <= x1 and (y in {y0, y1})


def _page_svg(model, page_id):
    return render_pages(model)[f"{page_id.kind}:{page_id.value}"]


# -- D10 ------------------------------------------------------------------------------------


def test_a_units_boundary_stub_names_the_outermost_carrier_then_the_far_end() -> None:
    """D10: stub text is the outermost carrier (-W3, not -W1), an arrow, the far end."""
    # UNDO: fransys_layout/engines/schematic/read/offstubs.py: `end_text` stops walking to the
    #   top carrier (drop the `while carrier ... parent` loop, so the cable -W1 is named)
    stubs = _stubs(_off_stub_model(), own_set=True)
    (stub,) = stubs  # HL18, owner C1: the line -W3 leaves X1 in one stub, not one per pin
    assert "line_stub" in stub.key
    text = marker_text(_off_stub_model(), stub)
    assert text.startswith("-W3 ")
    assert text[len("-W3 ")] in _ARROWS
    assert "+FLD" in text
    assert ":" not in text  # HL18: the harness draws as a line, so its stub names no far port


def test_the_unit_side_of_a_mated_top_level_cable_reads_like_the_top_level_side() -> None:
    """D10: a cable mated at a unit's boundary is drawn the same from the unit's side."""
    # UNDO: fransys_layout/engines/schematic/read/offstubs.py: `boundary_offs` returns no
    #   off-stub for a unit's boundary pins, or `full_port` names the far end differently from
    #   the plug side
    model = _off_stub_model()
    own = _stubs(model, own_set=True)
    boundary = {_port_function(model, m) for m in own}  # HL18: a line's stub stands at X1
    plug_side = {
        _normal(marker_text(model, m))
        for m in _stubs(model, own_set=False)
        if _port_function(model, m) in boundary
    }
    unit_side = {_normal(marker_text(model, m)) for m in own}
    assert unit_side
    assert unit_side == plug_side


def _port_function(model, marker):
    from fransys_model.vocab.tables import ports

    return ports(model)[marker.port].function


def test_every_stub_row_shares_one_box_and_every_wire_ends_on_it() -> None:
    """D10: a run of stubs gets one box at least as wide as the run; every wire ends on its box.
    Single wires: a line's conductors leave in one stub (HL18), so no run to share a box."""
    # UNDO: fransys_layout/stages/references/off_stubs.py: `_runs` `if any(before[0] < at <
    #   end[0] for at in cuts):` -> `if True:` (each stub its own box; verified by probe). The
    #   run-width rule alone is not caught here: only the shared box and the wire ends are pinned
    model = _two_location_wires_model()
    first, *_ = _off_stubs(model)
    stubs = [m for m in _off_stubs(model) if m.page == first.page]
    assert len(stubs) == 2
    assert len({(m.y, m.width, m.height) for m in stubs}) == 1
    assert stubs[0].width >= max(m.x for m in stubs) - min(m.x for m in stubs)
    boxes, ends = _svg_boxes_and_stubs(_page_svg(model, stubs[0].page))
    assert len(boxes) == 1
    assert len(ends) == len(stubs)
    assert all(_on_box_edge(boxes[0], end) for end in ends)


@pytest.mark.parametrize(
    ("build", "least"), [(_off_stub_model, 2), (_system_model, 6)], ids=["off-stub", "system"]
)
def test_every_wire_of_every_stub_on_every_page_ends_on_a_box(build, least) -> None:
    """D10: on every page of both fixtures, each stub's wire ends on the edge of a marker box.
    The off-stub fixture's W3 is a line: one stub per set it leaves (HL18), no per-pin stubs;
    the line itself runs on to its stub's box, which draws no stub (layout-0158)."""
    # UNDO: fransys_render/_markers.py: `_stub_glyph` ends the stub one grid short of the box
    #   edge
    model = build()
    seen = 0
    for page in layout_of(model, Page).values():
        boxes, ends = _svg_boxes_and_stubs(_page_svg(model, page.id))
        markers = [m for m in layout_of(model, LinkMarker).values() if m.page == page.id]
        if not markers:  # a page without stubs draws other "marker" lines (contact-image ticks)
            continue
        lines = [m for m in markers if m.carrier is not None and draws_as_line(model, m.carrier)]
        assert len(ends) == len(markers) - len(lines)
        for end in ends:
            assert any(_on_box_edge(box, end) for box in boxes), end
        line_ends = _harness_line_ends(_page_svg(model, page.id))
        assert sum(any(_on_box_edge(box, end) for box in boxes) for end in line_ends) == len(lines)
        seen += len(ends) + len(lines)
    assert seen >= least


def test_a_top_level_stub_prints_the_carrier_and_the_far_ends_product_designation() -> None:
    """D10: top-level stubs read "-WM1 -> +ER+C1-X2:1", no function segment."""
    # UNDO: fransys_model/derive/drawing_text.py: `stub_far_end` (which `full_port` in
    #   engines/schematic/read/offstubs.py calls) `product_designation` -> `reference_designation`
    #   (the two-location cable below has far ends with a function segment: "=G+B-P2" would
    #   print)
    model = _system_model()
    texts = {_normal(marker_text(model, m)) for m in _stubs(model, own_set=False)}
    arrow = "→"
    assert texts == {
        f"-WM1 {arrow} +ER+C1-X2:1",
        f"-WM2 {arrow} +ER+C2-X2:1",
        f"-WM1S {arrow} +ER+C1-X2:2",
        f"-WM2S {arrow} +ER+C2-X2:2",
    }
    # far ends that DO stand in a function group "=G": still named "+B-P2", "+A-P1"; the
    # two-core W1 is a line, one stub per set (HL18, owner C1)
    cable = _two_location_cable_model()
    assert sorted(_normal(marker_text(cable, m)) for m in _stubs(cable, own_set=False)) == [
        f"-W1 {arrow} +A-P1",
        f"-W1 {arrow} +B-P2",
    ]


def test_a_unit_side_stub_names_a_top_level_far_end_without_its_function_segment() -> None:
    """D10: a cabinet-set stub to the motor reads "+FLD-M1:U", no "=FLD"."""
    # UNDO: fransys_model/derive/drawing_text.py: `stub_far_end` (which `full_port` in
    #   engines/schematic/read/offstubs.py calls) `product_designation` -> `reference_designation`
    #   (the unit-side text gains "=FLD")
    model = _system_model()
    texts = {_normal(marker_text(model, m)) for m in _stubs(model, own_set=True)}
    arrow = "→"
    assert texts == {
        f"-WM1 {arrow} +FLD-M1:U",
        f"-WM2 {arrow} +FLD-M2:U",
        f"-WM1S {arrow} +FLD-K1:1",
        f"-WM2S {arrow} +FLD-K1:2",
    }


def _off_stubs(model):
    return [m for m in layout_of(model, LinkMarker).values() if m.star is StarKind.OFF]


def test_an_off_stub_box_is_shared_only_by_stubs_of_one_carrier_and_one_far_device() -> None:
    """D10, EF-C part 5: off stubs of one page, `box_x` and `y` name one cable and far item.

    HL11 (layout-0153): the system's boards are middle outlines, so their cabinet columns lose
    the X1 and P1 views and no stub there turns or shares a box. A line leaves in one stub
    (HL18), so single wires to two far devices make the shared boxes.
    """
    # UNDO: fransys_layout/stages/references/off_stubs.py: the `rows[...]` key and the `pins`
    #   destination drop `end_text.cable, end_text.far` for `"", ""` (stubs to Q1 and Q2 share a
    #   box; verified by probe)
    model = _build_two_connectors(relay_between=False, lines=False)
    named: dict = defaultdict(set)
    for m in _off_stubs(model):
        if m.box_x is not None:
            named[m.page, m.box_x, m.y].add((m.carrier, stub_far_end(model, m.far)[0]))
    assert named
    assert all(len(names) == 1 for names in named.values())


def test_stubs_of_different_row_keys_on_one_row_stand_in_boxes_side_by_side() -> None:
    """D10, EF-C part 5: on one page and `y`, stubs that name different cables or far ends never
    share a box; their boxes stand clear of each other. Each of the fixture's 8 stubs is named."""
    # UNDO: stages/texts/marker_row.py: `place_markers` takes each marker's first candidate place
    #   without asking Room whether it is free (-WM1S and -WM2S on the field wiring page overlap)
    model = _system_model()
    arrow = "→"
    assert sorted(_normal(marker_text(model, m)) for m in _off_stubs(model)) == sorted(
        f"{cable} {arrow} {far}"
        for cable, far in [
            ("-WM1", "+ER+C1-X2:1"),
            ("-WM2", "+ER+C2-X2:1"),
            ("-WM1S", "+ER+C1-X2:2"),
            ("-WM2S", "+ER+C2-X2:2"),
            ("-WM1", "+FLD-M1:U"),
            ("-WM2", "+FLD-M2:U"),
            ("-WM1S", "+FLD-K1:1"),
            ("-WM2S", "+FLD-K1:2"),
        ]
    )
    rows: dict = defaultdict(list)
    for m in _off_stubs(model):
        if m.lead:  # one row per box (M3): a lead stands for every stub sharing its box
            # a vertical N/S box stands centred on the pin unless `box_x` moves it (M1)
            left = m.box_x if m.box_x is not None else m.x - (m.width // 2 if m.vertical else 0)
            row = (left, left + m.width, marker_text(model, m), m.stub_extra, m.height)
            rows[m.page, m.y].append(row)
    pairs = [sorted(boxes) for boxes in rows.values() if len(boxes) > 1]
    # the motors' page (two U boxes beyond their sibling lanes: D14), the two pump cabinets'
    # pages (X2:1 and X2:2, staggered on two tiers: GOLDEN-FIX 2) and the field wiring page
    assert len(pairs) == 4
    for (_, right, _, near, height), (left, _, _, other, other_height) in pairs:
        # side by side, or one tier's box (its extent along the stub, `stub_extra` out, its own
        # height thick) wholly clear of the other's: never overlapping
        assert right <= left or near + height <= other or other + other_height <= near
    assert all(len({row[2] for row in boxes}) == len(boxes) for boxes in pairs)


def test_stubs_of_one_row_key_share_one_box_listing_every_far_port() -> None:
    """D10, EF-C part 5: one carrier to one far device, two pins: one box per page, one text.
    Single wires: a two-core cable is a line, one stub per page naming no port (HL18)."""
    # UNDO: fransys_layout/stages/references/off_stubs.py: `_runs` `if any(before[0] < at <
    #   end[0] for at in cuts):` -> `if True:` (each stub its own run, its own box; by probe)
    model = _two_location_wires_model()
    stubs = _off_stubs(model)
    by_page = defaultdict(list)
    for m in stubs:
        by_page[m.page].append(m)
    assert len(stubs) == 4
    assert len(by_page) == 2
    for page_stubs in by_page.values():
        assert len({m.box_x for m in page_stubs}) == 1
        assert page_stubs[0].box_x is not None
        (text,) = {marker_text(model, m) for m in page_stubs}
        assert text.endswith(("+A-P1:1 2", "+B-P2:1 2"))  # every far port, in one text


# -- D11 ------------------------------------------------------------------------------------


def _top_level_page_with_outline(model):
    (page,) = {
        o.page for o in layout_of(model, Outline).values() if _set_of(model, o.page).unit is None
    }
    return page


def _placed(model, page, key_prefix):
    return [
        p
        for p in layout_of(model, SymbolPlacement).values()
        if p.page == page and functions(model)[p.function].key[: len(key_prefix)] == key_prefix
    ]


def _boxes(model, page, key_prefix):
    """The connector boxes on `page` of the functions keyed `key_prefix`, left to right."""
    found = [
        b
        for b in layout_of(model, ConnectorBox).values()
        if b.page == page and functions(model)[b.function].key[: len(key_prefix)] == key_prefix
    ]
    for b in found:
        lines = connector_box_lines(model, b.function, unit=_set_of(model, page).unit)
        assert len(b.texts) == len(lines)
        assert b.cells == ()  # a plug box and a unit interface box have no cells (HL5)
    return sorted(found, key=lambda b: b.x)


def _inside(outline, box) -> bool:
    return (
        outline.x <= box.x
        and box.x + box.width <= outline.x + outline.width
        and outline.y <= box.y
        and box.y + box.height <= outline.y + outline.height
    )


def test_a_units_outline_top_edge_stands_on_the_mating_line_with_the_plug_outside() -> None:
    """D11: the outline top sits on the mating line; the parent's plug is outside.
    HL6 (layout-0155): plug and boundary connector are boxes, face to face on that line."""
    # UNDO: fransys_layout/stages/outlines.py: `unit_outlines` ignores `mating` (top = min
    #   body y - margin)
    model = _off_stub_model()
    page = _top_level_page_with_outline(model)
    (outline,) = [o for o in layout_of(model, Outline).values() if o.page == page]
    (plug,) = _boxes(model, page, ("P1",))
    (boundary,) = _boxes(model, page, ("cab", "X1"))
    assert plug.y + plug.height == outline.y == boundary.y  # face to face on the mating line
    assert _inside(outline, boundary)


def _titles(model):
    """`{outline id: its title label}`."""
    found = {}
    for outline in layout_of(model, Outline).values():
        release = unit_release(model, outline.unit)
        (title,) = [
            lb
            for lb in layout_of(model, Label).values()
            if lb.page == outline.page
            and lb.slot == "outline_title"
            and label_text(model, lb)
            == f"{release.name} rev {revision_text(release.version, release.revision)}"
        ]
        found[outline.id] = title
    return found


def test_an_outline_title_is_above_left_when_that_is_free() -> None:
    """D11: the title stands above-left of its outline when that is free.

    Nothing stands above a top-level page's outline. A nested board at a harness line's end is a
    middle outline on its parent unit's page, its title inside (HL12, layout-0153).
    HL6 (layout-0155): boxes widen the outline; a title left of `TEXT_GAP` moves to it
    (layout-0104).
    """
    # UNDO: fransys_layout/stages/outlines.py: `unit_outlines` sets `title = below` always
    model = _system_model()
    outlines = layout_of(model, Outline)
    assert len(outlines) == 4
    height = default_profile().text_height
    above = 0
    inside = 0
    for outline_id, title in _titles(model).items():
        outline = outlines[outline_id]
        if _set_of(model, outline.page).unit is None:
            assert title.x == max(outline.x, TEXT_GAP)
            assert title.y + height < outline.y
            above += 1
        else:
            # HL12 (layout-0153): the board's X1 ends the harness WH1, so on its cabinet's page
            # the board is a middle outline, its title inside, left, between its two edges
            assert outline.x < title.x < outline.x + outline.width
            assert outline.y < title.y
            assert title.y + height < outline.y + outline.height
            inside += 1
    assert (above, inside) == (2, 2)


def test_an_outline_title_falls_below_left_when_the_plug_and_its_tag_take_the_space_above() -> None:
    """D11: with the parent's plug directly above the outline, the title goes below-left instead.
    Single wires: a unit with a line at an interface is a middle outline, title inside (HL12)."""
    # UNDO: fransys_layout/stages/outlines.py: `unit_outlines` sets `title = above` always
    model = _build_two_connectors(relay_between=False, lines=False)
    (outline,) = layout_of(model, Outline).values()
    (title,) = _titles(model).values()
    assert label_text(model, title) == "demo-pump-cabinet rev 1.1"
    assert title.x == max(outline.x, TEXT_GAP)  # layout-0104
    assert title.y >= outline.y + outline.height


def test_a_units_boundary_pins_in_neighbouring_columns_stand_in_one_outline() -> None:
    """D11: two boundary connectors in neighbouring columns share one outline: one per run.
    Single wires: with a line at an interface the unit is one middle outline (HL12, condition 1)."""
    # UNDO: fransys_layout/stages/outlines.py: `_column_runs` starts a new run for every
    #   column
    model = _build_two_connectors(relay_between=False, lines=False)
    page = _top_level_page_with_outline(model)
    (outline,) = [o for o in layout_of(model, Outline).values() if o.page == page]
    pins = [*_placed(model, page, ("cab", "X1")), *_placed(model, page, ("cab", "X2"))]
    assert len(pins) == 4
    assert all(outline.x <= p.x <= outline.x + outline.width for p in pins)
    assert outline.width > max(p.x for p in pins) - min(p.x for p in pins)


def test_a_column_that_is_not_the_units_cuts_its_outline_in_two() -> None:
    """D11: another column between two boundary connectors cuts the outline in two.
    Single wires: with a line at an interface the unit is one middle outline (HL12, condition 1)."""
    # UNDO: fransys_layout/stages/outlines.py: `_column_runs` never cuts (one run per
    #   unit)
    model = _build_two_connectors(relay_between=True, lines=False)
    page = _top_level_page_with_outline(model)
    left, right = sorted(
        (o for o in layout_of(model, Outline).values() if o.page == page), key=lambda o: o.x
    )
    x1, x2 = _placed(model, page, ("cab", "X1")), _placed(model, page, ("cab", "X2"))
    relay = _placed(model, page, ("K1",))
    assert relay
    assert len(x1) == len(x2) == 2
    assert all(left.x <= p.x <= left.x + left.width for p in x1)
    assert all(right.x <= p.x <= right.x + right.width for p in x2)
    assert left.x + left.width < min(p.x for p in relay) < max(p.x for p in relay) < right.x


def test_a_board_that_is_the_sole_root_of_its_unit_is_drawn_in_the_units_own_set() -> None:
    """D11: a sole-root board is drawn in its unit's own set, with no outline.
    HL6 (layout-0155): its `X1`, at a harness line's end, is drawn there as a connector box."""
    # UNDO: fransys_model/derive/structure.py: `schematic_functions` `excluded` -> `return True`
    #   (a sole-root board's contents are dropped from the schematic)
    model = _system_model()
    board_sets = [
        s
        for s in layout_of(model, DrawingSet).values()
        if s.unit and unit_release(model, s.unit).name == "demo-io-board"
    ]
    assert len(board_sets) == 2
    for drawing_set in board_sets:
        pages = {p.id for p in layout_of(model, Page).values() if p.drawing_set == drawing_set.id}
        drawn = {
            functions(model)[p.function].key[-3]
            for p in layout_of(model, SymbolPlacement).values()
            if p.page in pages
        }
        drawn |= {
            functions(model)[b.function].key[-3]
            for b in layout_of(model, ConnectorBox).values()
            if b.page in pages
            and len(b.texts) == len(connector_box_lines(model, b.function, unit=drawing_set.unit))
            and b.cells == ()
        }
        assert {"k1", "X1"} <= drawn
        assert not [o for o in layout_of(model, Outline).values() if o.page in pages]


def test_a_top_level_plug_at_a_units_location_does_not_take_the_location_from_the_unit() -> None:
    """D11: a harness plug at +C1 does not take +C1 from the cabinet unit."""
    # UNDO: fransys_model/derive/designation.py: `own_nodes` counts cable and harness items again
    model = _off_stub_model()
    (cabinet,) = units(model)
    own = {aspect_nodes(model)[n].label for n in own_nodes(model, cabinet)}
    assert {"C1", "NET"} <= own


def test_a_node_holding_a_top_level_device_is_not_the_units_own() -> None:
    """D11: a node holding a top-level device is not the unit's own."""
    # UNDO: fransys_model/derive/designation.py: `own_nodes` returns every node any of the unit's
    #   items touches
    model = _system_model()
    cabinet = next(
        u for u in units(model).values() if unit_release(model, u.id).name == "demo-pump-cabinet"
    )
    nodes = aspect_nodes(model)
    own = {
        nodes[n].label for n in own_nodes(model, cabinet.id) if nodes[n].aspect is Aspect.LOCATION
    }
    assert len(own & {"C1", "C2"}) == 1  # its own location
    assert not own & {"FLD", "ER"}  # the motors' location, and the one that holds both cabinets
