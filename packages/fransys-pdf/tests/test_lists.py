"""The six list/BOM pages (spec P9): real rows render, an empty list has no page."""

import re
from dataclasses import replace
from itertools import pairwise

import typst
from _build import (
    bridged_terminal,
    cable_facet,
    cable_product_facet,
    conductor,
    connector,
    document,
    external_port,
    item,
    location,
    model,
    part,
    pcb_facet,
    pin,
    place,
    plc_channel,
    terminal,
    unit,
    wire_facet,
)
from fransys_pdf import _lists, source
from fransys_pdf._lists import (
    _bridge_geometry,
    _bridge_lane_x_mm,
    _bridge_lanes,
    _BridgeMark,
    _terminal_table,
    bom_page,
    cable_list_page,
    connector_list_page,
    connector_rows_for,
    plc_channel_rows_for,
    terminal_list_page,
    wire_rows_for,
)

from fransys_model.derive import (
    BOM_COLUMNS,
    CABLE_LIST_COLUMNS,
    CONNECTOR_COLUMNS,
    DESIGNATION_COLUMNS,
    PIN_COLUMNS,
    PLC_COLUMNS,
    WIRE_COLUMNS,
    cable_list_rows,
    designation_list,
    document_unit,
    item_designation,
    terminal_rows,
    terminal_strips,
)
from fransys_model.kernel import make_id
from fransys_model.vocab import (
    ConductorKind,
    DocumentPreset,
    Mate,
    Net,
    NetClass,
    PageKind,
    Port,
    PortRole,
    SignalType,
    documents,
)

K = PageKind
# Named non-zero counts for the unit-scoping fixtures below (a nested unit's own rows and the
# top-level BOM's `TOP_LEVEL` unit line are both real content, not absence).
_TOP_LEVEL_BOM_LINE_COUNT = 1
_CABLE_LIST_ROW_COUNT = 2
_UNIT_OWN_STRIP_COUNT = 1
_UNIT_OWN_BOARD_COUNT = 1


def _cabinet(*, add=(), remove=()):
    """A `CABINET_SCHEMATIC` document about a fresh location, no notes."""
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        notes=None,
        add=add,
        remove=remove,
    )
    return c1, doc


def test_plc_list_renders_channel_rows():
    c1, doc = _cabinet(remove=(K.SCHEMATIC, K.TERMINAL_LIST, K.BOM))
    module = item("mod1", description="PLC module")
    module_part, template, fn, facet = plc_channel(
        "ch1", module=module.id, name="ch1", signal=SignalType.DI, channel=1
    )
    m = model(c1, doc, module, module_part, template, fn, facet)
    text = source(m, doc.id, {})
    assert '"Channel designation"' in text
    assert '"-MOD1:1"' in text
    assert '"di"' in text


def test_plc_list_leaves_the_page_out_for_no_channels():
    c1, doc = _cabinet(remove=(K.SCHEMATIC, K.TERMINAL_LIST, K.BOM))
    m = model(c1, doc)
    text = source(m, doc.id, {})
    assert "None." not in text
    assert '#heading(level: 1, text("Cover"))' in text  # the cover is still there
    assert text.count("#pagebreak()") == 0  # the cover alone: the empty list has no page (pdf-0019)


def test_terminal_list_renders_two_strips_with_heading_and_pagebreak():
    c1, doc = _cabinet(remove=(K.SCHEMATIC, K.PLC_LIST, K.BOM))
    strip1 = item("x1", description="Strip one")
    strip2 = item("x2", description="Strip two")
    # An unplaced strip proves the scoping is a real intersection with `items_at`, not "every
    # strip in the model": if `_terminal_strips_for` regressed to the latter, X3 would show up.
    strip3 = item("x3", description="Strip three, not placed anywhere")
    t1, t1_facet = terminal("t1", strip=strip1.id, group="L", index=1)
    t2, t2_facet = terminal("t2", strip=strip2.id, group="L", index=1)
    t3, t3_facet = terminal("t3", strip=strip3.id, group="L", index=1)
    p1 = place("p1", item=strip1.id, node=c1.id)
    p2 = place("p2", item=strip2.id, node=c1.id)
    m = model(c1, doc, strip1, strip2, strip3, t1, t1_facet, t2, t2_facet, t3, t3_facet, p1, p2)
    text = source(m, doc.id, {})
    assert text.count("#heading(level: 2,") == 2
    assert text.index('"-X1"') < text.index('"-X2"')
    assert '"-X1:L:1"' in text
    assert "X3" not in text
    assert text.count("#pagebreak()") == 2  # COVER|TERMINAL_LIST, then between the two strips


def test_terminal_list_leaves_the_page_out_for_no_strips_at_the_location():
    c1, doc = _cabinet(remove=(K.SCHEMATIC, K.PLC_LIST, K.BOM))
    m = model(c1, doc)
    text = source(m, doc.id, {})
    assert "None." not in text
    assert '#heading(level: 1, text("Cover"))' in text  # the cover is still there
    assert text.count("#pagebreak()") == 0  # the cover alone: the empty list has no page (pdf-0019)
    assert "#heading(level: 2," not in text


def test_terminal_list_leaves_the_page_out_for_an_item_subject():
    board = item("jb2", description="Invented board")
    doc = document(
        "d1",
        preset=DocumentPreset.PCB_SCHEMATIC,
        subject=board,
        cover="# Cover",
        notes=None,
        add=(K.TERMINAL_LIST,),
        remove=(K.SCHEMATIC, K.CONNECTOR_LIST, K.BOM),
    )
    m = model(board, doc)
    text = source(m, doc.id, {})
    assert "None." not in text
    assert '#heading(level: 1, text("Cover"))' in text  # the cover is still there
    assert text.count("#pagebreak()") == 0  # the cover alone: the empty list has no page (pdf-0019)


def test_bridge_geometry_splits_a_group_around_an_unbridged_terminal():
    """Spec T2 acceptance 2: the line still runs through the unbridged row, no tick there."""
    groups = (1, None, 1)  # row 1 is the unbridged terminal splitting group 1
    assert _bridge_geometry(groups) == (
        (_BridgeMark(top=False, bottom=True, tick=True),),
        (_BridgeMark(top=True, bottom=True, tick=False),),
        (_BridgeMark(top=True, bottom=False, tick=True),),
    )


def test_bridge_lanes_two_overlapping_groups_take_two_lanes():
    spans = {1: (0, 4), 2: (1, 3)}  # group 2's span nests inside group 1's: they overlap
    assert _bridge_lanes(spans) == {1: 0, 2: 1}


def test_bridge_lanes_two_non_overlapping_groups_share_one_lane():
    spans = {1: (0, 1), 2: (2, 3)}
    assert _bridge_lanes(spans) == {1: 0, 2: 0}


def test_bridge_geometry_two_overlapping_groups_one_split_by_an_unbridged_terminal():
    """The combined acceptance-2 fixture: group 1 spans rows 0-4 (row 2 unbridged, splitting
    it); group 2 spans rows 1-3, overlapping group 1's span, so it takes a second lane."""
    groups = (1, 2, None, 2, 1)
    geometry = _bridge_geometry(groups)
    # lane 0 is group 1's (processed first, group-number order), spanning rows 0-4 whole;
    # lane 1 is group 2's, spanning rows 1-3 -- each group's own line is continuous across
    # its full span, in its own lane, whatever the other group is doing in the rows between.
    assert geometry[0] == (_BridgeMark(top=False, bottom=True, tick=True), None)
    assert geometry[1] == (
        _BridgeMark(top=True, bottom=True, tick=False),
        _BridgeMark(top=False, bottom=True, tick=True),
    )
    assert geometry[2] == (
        _BridgeMark(top=True, bottom=True, tick=False),
        _BridgeMark(top=True, bottom=True, tick=False),
    )
    assert geometry[3] == (
        _BridgeMark(top=True, bottom=True, tick=False),
        _BridgeMark(top=True, bottom=False, tick=True),
    )
    assert geometry[4] == (_BridgeMark(top=True, bottom=False, tick=True), None)


def test_bridge_geometry_many_non_overlapping_groups_share_one_lane():
    """Regression, can-fail (review): `_bridge_geometry` must count *distinct* lanes used,
    not one per group. 30 independent (non-overlapping) pairs all reuse lane 0 -- if
    `lane_count` were `len(lanes)` (30, one per group) instead of the number of lanes
    actually used (1), `_bridge_lane_x_mm(30)` would spread every mark from about -36mm to
    +51mm, off the fixed 15mm column and under the next column over (Internal ends).
    """
    groups = tuple(group for group in range(1, 31) for _ in range(2))  # 1,1,2,2,...,30,30
    geometry = _bridge_geometry(groups)
    lane_count = len(geometry[0])
    assert lane_count == 1
    lane_xs = _bridge_lane_x_mm(lane_count)
    assert lane_xs == (7.5,)  # inside [0, 15]: the column's own width
    for row_marks in geometry:
        assert len(row_marks) == 1
        assert row_marks[0] is not None


def test_bridge_lane_x_mm_centres_lanes_in_the_15mm_column_3mm_apart():
    """Spec T2 amendment: a fixed 15 mm Bridge column, lanes centred, 3 mm apart."""
    assert _bridge_lane_x_mm(1) == (7.5,)
    assert _bridge_lane_x_mm(2) == (6.0, 9.0)
    assert _bridge_lane_x_mm(3) == (4.5, 7.5, 10.5)


def test_terminal_list_bridge_column_renders_lines_and_ticks_for_a_bridged_strip():
    """Integration proof: `source()` really wires `_bridge_geometry` into the TERMINAL_LIST
    page for a strip with one jumper group split by an unbridged terminal (spec T2, pdf-0007).
    """
    c1, doc = _cabinet(remove=(K.PLC_LIST, K.SCHEMATIC, K.BOM))
    strip = item("x1", description="Strip one")
    t1, t1_facet, t1_fn, t1_port = bridged_terminal("t1", strip=strip.id, group="T", index=1)
    t2, t2_facet, t2_fn, t2_port = bridged_terminal("t2", strip=strip.id, group="T", index=2)
    t3, t3_facet, t3_fn, t3_port = bridged_terminal("t3", strip=strip.id, group="T", index=3)
    jumper = conductor("j1", a=t1_port.id, b=t3_port.id, kind=ConductorKind.JUMPER)
    p1 = place("p1", item=strip.id, node=c1.id)
    m = model(
        c1,
        doc,
        strip,
        t1,
        t1_facet,
        t1_fn,
        t1_port,
        t2,
        t2_facet,
        t2_fn,
        t2_port,
        t3,
        t3_facet,
        t3_fn,
        t3_port,
        jumper,
        p1,
    )
    text = source(m, doc.id, {})
    assert '"Bridge"' in text
    assert '"Jumper group"' not in text
    assert "15mm" in text  # spec T2 amendment: the fixed column width
    assert text.count("table.cell(inset: 0pt, breakable: false)") == 3  # one per row
    # one lane, centred at 7.5mm (_bridge_lane_x_mm(1)):
    assert text.count("(7.5mm, 0%)") == 2  # top half starts: rows T:2 and T:3
    assert text.count("end: (7.5mm, 100%)") == 2  # bottom half ends: rows T:1 and T:2
    assert text.count("(6.5mm, 50%)") == 2  # ticks: rows T:1 and T:3 (members)


def test_terminal_table_spans_full_width_with_both_sides_as_1fr():
    """Designer ruling (2026-09-23, decision pdf-0008, amended by pdf-0011 F1): the terminal
    list's table spans the page's full content width -- Side A and Side B (`internal_ends`,
    `external_ends`) are `1fr` of equal weight, the rest of `_TERMINAL_DATA` `auto`, Bridge
    the fixed 15mm. This strip has neither side, so it exercises the fallback only; the
    compiled equal-width check is `test_terminal_list_side_a_and_side_b_compile_equally_wide`.
    Every other list page (`_table()`: PLC, BOM, wire label,
    designation, cable, connector) now spans full width the same way, each with its own
    `wide` column -- `test_every_list_table_spans_full_width_with_exactly_one_1fr_column`
    below covers those six.
    """
    c1, doc = _cabinet(remove=(K.PLC_LIST, K.SCHEMATIC, K.BOM))
    strip = item("x1", description="Strip one")
    t1, t1_facet = terminal("t1", strip=strip.id, group="L", index=1)
    p1 = place("p1", item=strip.id, node=c1.id)
    m = model(c1, doc, strip, t1, t1_facet, p1)
    text = source(m, doc.id, {})
    # Pdf-0011: this strip has no internal/external ends and no jumper group, so those two
    # columns and the Bridge column are not drawn; `internal_ends` was the only `1fr`, so the
    # last remaining data column (`index`) takes it. The strip-with-jumper test below covers
    # the Bridge column and the `1fr` staying on `internal_ends`.
    assert "columns: (auto, auto, 1fr)" in text
    assert '"Bridge"' not in text


def test_internal_ends_drops_a_jumper_partner_but_keeps_a_wire_partner():
    """Spec T2 amendment: a jumper partner leaves Internal ends (the Bridge column already
    shows it); a real wire's far end is unaffected. `terminal_rows` itself is unchanged --
    both conductors are still in the model and in `TerminalRow.internal`, only the rendered
    text drops the jumper's.
    """
    c1, doc = _cabinet(remove=(K.PLC_LIST, K.SCHEMATIC, K.BOM))
    strip = item("x1", description="Strip one")
    t1, t1_facet, t1_fn, t1_port = bridged_terminal("t1", strip=strip.id, group="T", index=1)
    t2, t2_facet, t2_fn, t2_port = bridged_terminal("t2", strip=strip.id, group="T", index=2)
    far_item, far_fn, far_port = pin("far", "K1:A1")
    jumper = conductor("j1", a=t1_port.id, b=t2_port.id, kind=ConductorKind.JUMPER)
    wire = conductor("w1", a=t1_port.id, b=far_port.id)
    p1 = place("p1", item=strip.id, node=c1.id)
    m = model(
        c1,
        doc,
        strip,
        t1,
        t1_facet,
        t1_fn,
        t1_port,
        t2,
        t2_facet,
        t2_fn,
        t2_port,
        far_item,
        far_fn,
        far_port,
        jumper,
        wire,
        p1,
    )
    text = source(m, doc.id, {})
    assert '"-K1:A1:1"' in text  # the wire's far end: kept
    # Ports print dashed. T:2's own designation cell already reads `-X1:T:2` (and T:1's reads
    # `-X1:T:1`), so a jumper partner left in an ends cell shows up as a second occurrence.
    parts = _cell_parts(text)
    assert parts.count("-X1:T:2") == 1  # the jumper's far end (T:1's partner): dropped
    assert parts.count("-X1:T:1") == 1  # and T:2's partner, T:1, likewise


def test_connector_list_renders_two_boards_with_heading_and_pagebreak():
    c1, doc = _cabinet(
        add=(K.CONNECTOR_LIST,), remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM)
    )
    board1_part = part("board1", description="Invented board one")
    board1 = item("jb1", description="Board one", part=board1_part.id)
    pcb1 = pcb_facet("board1", subject=board1_part.id)
    board2_part = part("board2", description="Invented board two")
    board2 = item("jb2", description="Board two", part=board2_part.id)
    pcb2 = pcb_facet("board2", subject=board2_part.id)
    conn1_part, conn1_template, conn1_fn, conn1_facet, conn1_ports = connector(
        "j1", item=board1.id, name="J1", markings=("1", "2")
    )
    conn2_part, conn2_template, conn2_fn, conn2_facet, conn2_ports = connector(
        "j2", item=board2.id, name="J2", markings=("1",)
    )
    # A board placed at a DIFFERENT location proves the scoping is a real intersection with
    # `items_at`, not "every board in the model": if `_boards_for` regressed to the latter,
    # JB9 would show up even though it sits under C9, not the document's own location C1.
    c9 = location("C9", "Other cabinet")
    board9_part = part("board9", description="Invented board elsewhere")
    board9 = item("jb9", description="Board elsewhere", part=board9_part.id)
    pcb9 = pcb_facet("board9", subject=board9_part.id)
    conn9_part, conn9_template, conn9_fn, conn9_facet, conn9_ports = connector(
        "j9", item=board9.id, name="J9", markings=("1",)
    )
    p1 = place("p1", item=board1.id, node=c1.id)
    p2 = place("p2", item=board2.id, node=c1.id)
    p9 = place("p9", item=board9.id, node=c9.id)
    m = model(
        c1,
        c9,
        doc,
        board1_part,
        board1,
        pcb1,
        board2_part,
        board2,
        pcb2,
        board9_part,
        board9,
        pcb9,
        conn1_part,
        conn1_template,
        conn1_fn,
        conn1_facet,
        *conn1_ports,
        conn2_part,
        conn2_template,
        conn2_fn,
        conn2_facet,
        *conn2_ports,
        conn9_part,
        conn9_template,
        conn9_fn,
        conn9_facet,
        *conn9_ports,
        p1,
        p2,
        p9,
    )
    text = source(m, doc.id, {})
    assert text.count("#heading(level: 2,") == 2
    assert text.index('"-JB1"') < text.index('"-JB2"')
    # The heading alone would already contain `"-JB1"`; the designation *cell* is what proves
    # the row itself, so pair it with the adjacent style cell no heading ever carries.
    assert 'text("-JB1"), text("header")' in text
    assert "JB9" not in text
    assert text.count("#pagebreak()") == 2  # COVER|CONNECTOR_LIST, then between the two boards


def test_connector_list_renders_rows_for_an_item_subject_board():
    board_part = part("boarditem", description="Invented board")
    board = item("jb3", description="Invented board", part=board_part.id)
    pcb = pcb_facet("boarditem", subject=board_part.id)
    conn_part, template, fn, facet, ports = connector(
        "j3", item=board.id, name="J1", markings=("1",)
    )
    doc = document(
        "d1",
        preset=DocumentPreset.PCB_SCHEMATIC,
        subject=board,
        cover="# Cover",
        notes=None,
        remove=(K.SCHEMATIC, K.BOM),
    )
    m = model(board_part, board, pcb, conn_part, template, fn, facet, *ports, doc)
    text = source(m, doc.id, {})
    # The heading alone would already contain `"JB3"`; the designation *cell* is what proves
    # the row itself, so pair it with the adjacent style cell no heading ever carries.
    assert 'text("-JB3"), text("header")' in text
    assert text.count("#heading(level: 2,") == 1


def test_connector_list_leaves_the_page_out_for_no_boards():
    c1, doc = _cabinet(
        add=(K.CONNECTOR_LIST,), remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM)
    )
    m = model(c1, doc)
    text = source(m, doc.id, {})
    assert "None." not in text
    assert '#heading(level: 1, text("Cover"))' in text  # the cover is still there
    assert text.count("#pagebreak()") == 0  # the cover alone: the empty list has no page (pdf-0019)


def test_wire_label_list_renders_rows():
    c1, doc = _cabinet(
        add=(K.WIRE_LABEL_LIST,), remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM)
    )
    a_item, a_fn, a_port = pin("p1", "P1")
    b_item, b_fn, b_port = pin("p2", "P2")
    cond = conductor("w1", a=a_port.id, b=b_port.id)
    wf = wire_facet("w1", subject=cond.id, label="W1")
    m = model(c1, doc, a_item, a_fn, a_port, b_item, b_fn, b_port, cond, wf)
    text = source(m, doc.id, {})
    assert '"From"' in text
    assert '"Label"' in text
    assert '"-P1:1"' in text
    assert '"-P1:1 -P2:1"' in text or '"-P2:1 -P1:1"' in text  # V8: both ends, one space


def test_wire_label_list_leaves_the_page_out_for_no_wires():
    c1, doc = _cabinet(
        add=(K.WIRE_LABEL_LIST,), remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM)
    )
    m = model(c1, doc)
    text = source(m, doc.id, {})
    assert "None." not in text
    assert '#heading(level: 1, text("Cover"))' in text  # the cover is still there
    assert text.count("#pagebreak()") == 0  # the cover alone: the empty list has no page (pdf-0019)


def test_designation_list_renders_rows():
    c1, doc = _cabinet(
        add=(K.DESIGNATION_LIST,), remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM)
    )
    demo = item("k1", description="Invented relay")
    m = model(c1, doc, demo)
    text = source(m, doc.id, {})
    assert '"Designation"' in text
    assert '"-K1"' in text
    assert '"Invented relay"' in text


def test_designation_list_leaves_the_page_out_for_no_items():
    c1, doc = _cabinet(
        add=(K.DESIGNATION_LIST,), remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM)
    )
    m = model(c1, doc)
    text = source(m, doc.id, {})
    assert "None." not in text
    assert '#heading(level: 1, text("Cover"))' in text  # the cover is still there
    assert text.count("#pagebreak()") == 0  # the cover alone: the empty list has no page (pdf-0019)


def test_bom_renders_rows():
    c1, doc = _cabinet(remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST))
    demo_part = part("relay", description="Invented relay")
    demo_item = item("k1", description="Invented relay", part=demo_part.id)
    placement = place("p1", item=demo_item.id, node=c1.id)
    m = model(c1, doc, demo_part, demo_item, placement)
    text = source(m, doc.id, {})
    assert '"Mpn"' in text
    assert '"SIM-RELAY"' in text
    assert '"-K1"' in text  # designations column


def test_bom_leaves_the_page_out_for_empty_scope():
    c1, doc = _cabinet(remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST))
    m = model(c1, doc)
    text = source(m, doc.id, {})
    assert "None." not in text
    assert '#heading(level: 1, text("Cover"))' in text  # the cover is still there
    assert text.count("#pagebreak()") == 0  # the cover alone: the empty list has no page (pdf-0019)


def _unit_document(u, *, add=(), remove=()):
    """A `CABINET_SCHEMATIC` document about `u` (a `Unit`), no notes (units spec U3)."""
    return document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=u,
        cover="# Cover",
        notes=None,
        add=add,
        remove=remove,
    )


def test_plc_list_scoped_to_the_documents_unit():
    """Units spec U6: a unit document's PLC list keeps only rows whose module belongs to that
    unit directly. `MOD2` (no unit) is real model content that must NOT leak in -- can-fail
    below drops the `unit=` argument and shows it wrongly appearing."""
    u = unit("u1", name="pump-cabinet")
    doc = _unit_document(u, remove=(K.SCHEMATIC, K.TERMINAL_LIST, K.BOM))
    mod_in = item("mod1", description="PLC module", unit=u.id)
    mod_out = item("mod2", description="Other module")
    part_in, tmpl_in, fn_in, facet_in = plc_channel(
        "ch1", module=mod_in.id, name="ch1", signal=SignalType.DI, channel=1
    )
    part_out, tmpl_out, fn_out, facet_out = plc_channel(
        "ch2", module=mod_out.id, name="ch2", signal=SignalType.DI, channel=1
    )
    m = model(
        u,
        doc,
        mod_in,
        mod_out,
        part_in,
        tmpl_in,
        fn_in,
        facet_in,
        part_out,
        tmpl_out,
        fn_out,
        facet_out,
    )
    text = source(m, doc.id, {})
    assert '"-MOD1:1"' in text
    assert '"-MOD2:1"' not in text


def test_wire_label_list_scoped_to_the_documents_unit():
    """Units spec U6: a unit document's wire-label list keeps only conductors that belong to
    that unit (both ends' items in it). The unitless wire is real model content."""
    u = unit("u1", name="pump-cabinet")
    doc = _unit_document(u, add=(K.WIRE_LABEL_LIST,), remove=(K.SCHEMATIC, K.TERMINAL_LIST, K.BOM))
    a_in, fn_a_in, port_a_in = pin("a_in", "A1", unit=u.id)
    b_in, fn_b_in, port_b_in = pin("b_in", "B1", unit=u.id)
    cond_in = conductor("w_in", a=port_a_in.id, b=port_b_in.id)
    wf_in = wire_facet("w_in", subject=cond_in.id, label="WIN")
    a_out, fn_a_out, port_a_out = pin("a_out", "A2")
    b_out, fn_b_out, port_b_out = pin("b_out", "B2")
    cond_out = conductor("w_out", a=port_a_out.id, b=port_b_out.id)
    wf_out = wire_facet("w_out", subject=cond_out.id, label="WOUT")
    m = model(
        u,
        doc,
        a_in,
        fn_a_in,
        port_a_in,
        b_in,
        fn_b_in,
        port_b_in,
        cond_in,
        wf_in,
        a_out,
        fn_a_out,
        port_a_out,
        b_out,
        fn_b_out,
        port_b_out,
        cond_out,
        wf_out,
    )
    text = source(m, doc.id, {})
    assert '"-A1:1' in text
    assert '"-A2:1' not in text


def test_designation_list_scoped_to_the_documents_unit():
    """Units spec U6: a unit document's designation list keeps only items of that unit."""
    u = unit("u1", name="pump-cabinet")
    doc = _unit_document(u, add=(K.DESIGNATION_LIST,), remove=(K.SCHEMATIC, K.TERMINAL_LIST, K.BOM))
    demo_in = item("k1", description="Invented relay, in the unit", unit=u.id)
    demo_out = item("k2", description="Invented relay, not in the unit")
    # A second root: a unit's sole root has no designation row (UNIT-ID I4), which is not
    # what this test is about.
    demo_in_too = item("k3", description="Invented relay, also in the unit", unit=u.id)
    m = model(u, doc, demo_in, demo_out, demo_in_too)
    text = source(m, doc.id, {})
    assert '"-K1"' in text
    assert '"-K3"' in text
    assert '"-K2"' not in text


def test_terminal_list_scoped_to_the_documents_unit_direct_membership_only():
    """Units spec U6: a unit document's TERMINAL_LIST covers exactly that unit's own strips
    -- `Item.unit == record.unit` directly, never the recursive subtree. A nested unit's own
    strip (u2, child of u1) and an unrelated unitless strip are both real model content that
    must not leak into u1's own document."""
    u1 = unit("u1", name="top-unit")
    u2 = unit("u2", name="nested-unit", parent=u1.id)
    doc = _unit_document(u1, remove=(K.SCHEMATIC, K.PLC_LIST, K.BOM))
    strip_top = item("x1", description="Top unit's own strip", unit=u1.id)
    strip_nested = item("x2", description="Nested unit's own strip", unit=u2.id)
    strip_none = item("x3", description="Unitless strip", unit=None)
    # A second root: a unit's sole root prints no heading (UNIT-ID I4), which is not what
    # this test is about.
    second_root = item("k1", description="Top unit's second root", unit=u1.id)
    t1, t1_facet = terminal("t1", strip=strip_top.id, group="L", index=1)
    t2, t2_facet = terminal("t2", strip=strip_nested.id, group="L", index=1)
    t3, t3_facet = terminal("t3", strip=strip_none.id, group="L", index=1)
    m = model(
        u1,
        u2,
        doc,
        second_root,
        strip_top,
        strip_nested,
        strip_none,
        t1,
        t1_facet,
        t2,
        t2_facet,
        t3,
        t3_facet,
    )
    text = source(m, doc.id, {})
    assert text.count("#heading(level: 2,") == _UNIT_OWN_STRIP_COUNT  # only the top unit's own
    assert "X1" in text
    assert "X2" not in text  # nested unit's own strip: excluded, not just absent from a count
    assert "X3" not in text  # unitless: excluded too


def test_connector_list_scoped_to_the_documents_unit_direct_membership_only():
    """Units spec U6: a unit document's CONNECTOR_LIST covers exactly that unit's own boards
    -- direct `Item.unit == record.unit`, never the recursive subtree. A nested unit's own
    board (u2, child of u1) must not leak into u1's own document. This is also the shape that
    used to crash: before the fix, `_boards_for` asserted the document's own `location` was
    not `None`, which a unit-subject document violates; building this document's `source()`
    used to raise `AssertionError` here (the fix's own commit message records the can-fail
    probe: reverting `_boards_for` makes this test fail with that exact `AssertionError`)."""
    u1 = unit("u1", name="top-unit")
    u2 = unit("u2", name="nested-unit", parent=u1.id)
    board1_part = part("board1", description="Top unit's own board")
    board1 = item("jb1", description="Board one", part=board1_part.id, unit=u1.id)
    pcb1 = pcb_facet("board1", subject=board1_part.id)
    conn1_part, conn1_template, conn1_fn, conn1_facet, conn1_ports = connector(
        "j1", item=board1.id, name="J1", markings=("1",)
    )
    board2_part = part("board2", description="Nested unit's own board")
    board2 = item("jb2", description="Board two", part=board2_part.id, unit=u2.id)
    pcb2 = pcb_facet("board2", subject=board2_part.id)
    # A second root: a unit's sole root prints no heading (UNIT-ID I4), which is not what
    # this test is about.
    second_root = item("k1", description="Top unit's second root", unit=u1.id)
    doc = document(
        "d1",
        preset=DocumentPreset.PCB_SCHEMATIC,
        subject=u1,
        cover="# Cover",
        notes=None,
        remove=(K.SCHEMATIC, K.BOM),
    )
    m = model(
        u1,
        u2,
        doc,
        second_root,
        board1_part,
        board1,
        pcb1,
        conn1_part,
        conn1_template,
        conn1_fn,
        conn1_facet,
        *conn1_ports,
        board2_part,
        board2,
        pcb2,
    )
    text = source(m, doc.id, {})
    assert text.count("#heading(level: 2,") == _UNIT_OWN_BOARD_COUNT  # only the top unit's own
    # The heading alone would already contain `"JB1"`; the designation *cell* is what proves
    # the row itself, so pair it with the adjacent style cell no heading ever carries.
    assert 'text("-JB1"), text("header")' in text
    assert "JB2" not in text  # nested unit's own board: excluded, not just absent from a count


def test_terminal_and_connector_list_page_return_nothing_for_a_system_document():
    """Units spec U6 / spec P9: a `system` document has none of location, item and unit --
    both `_terminal_strips_for` and `_boards_for` return `()` through a plain `None`-location
    guard now, not the `assert location is not None` the old `_boards_for` raised on."""
    doc = document("d1", preset=DocumentPreset.SYSTEM, cover="# Cover", notes=None)
    m = model(doc)
    record = documents(m)[doc.id]
    assert terminal_list_page(m, record) == ""
    assert connector_list_page(m, record) == ""


def test_bom_page_for_system_preset_uses_top_level_scope():
    """Units spec U5: the `system` preset's BOM scopes to `derive.TOP_LEVEL` (items with no
    unit, plus one line per top-level unit), differing from `scope=None`'s whole-model result
    (which would also count the nested unit's own item -- `_TOP_LEVEL_BOM_LINE_COUNT` is the
    unit's own line, the nested item never appearing beside it). Calls `bom_page` directly:
    the `system` preset's own default pages are Part 4's, a later commit of this same work.
    """
    u = unit("u1", name="relay-interface-board")
    doc = document("d1", preset=DocumentPreset.SYSTEM, cover="# Cover", notes=None)
    nested_part = part("relay", description="Invented relay")
    nested_item = item("k1", description="Invented relay", part=nested_part.id, unit=u.id)
    m = model(u, doc, nested_part, nested_item)
    record = documents(m)[doc.id]
    text = bom_page(m, record)
    assert text.count('"relay-interface-board"') == _TOP_LEVEL_BOM_LINE_COUNT
    assert '"SIM-RELAY"' not in text  # the nested item's own MPN never appears at TOP_LEVEL


def test_every_list_table_applies_the_fr_vs_auto_convention_column_by_column(monkeypatch):
    """Designer ruling (2026-09-23, amended 2026-09-23, decision pdf-0008): "a column whose
    content has no length bound is `1fr` -- free text, or a joined list of designations or
    labels; a code-like column (MPN, revision, count, a single designation, a single terminal
    or pin) stays `auto`." Checked per list kind, every column named, not just "exactly one
    1fr" -- BOM and the cable list each have more than one unbounded column. The terminal
    list's own case (`internal_ends`) is covered separately above; this test covers the six
    built through the shared `_table()` helper.

    Pdf-0011: a column empty in every row is not drawn, and these fixtures leave many columns
    empty, so a rendered `columns:` string no longer names every column. This test therefore
    records the `wide` tuple each page hands `_table()` (the convention itself) and leaves the
    rendered result to the pdf-0011 tests below.
    """
    seen: list[tuple[tuple[str, ...], tuple[str, ...]]] = []
    real_table = _lists._table

    def spy(headers, rows, wide):
        seen.append((headers, wide))
        return real_table(headers, rows, wide)

    monkeypatch.setattr(_lists, "_table", spy)
    # PLC list: `wired_to` (a joined list of ends) and `signal_name` are unbounded (the rest are
    # a single designation or an enum).
    c1, doc = _cabinet(remove=(K.SCHEMATIC, K.TERMINAL_LIST, K.BOM))
    module = item("mod1", description="PLC module")
    module_part, template, fn, facet = plc_channel(
        "ch1", module=module.id, name="ch1", signal=SignalType.DI, channel=1
    )
    m = model(c1, doc, module, module_part, template, fn, facet)
    source(m, doc.id, {})
    assert seen[-1] == (PLC_COLUMNS, ("wired_to", "signal_name"))

    # BOM: `description` (free text) AND `designations` (a joined list) are both unbounded.
    c1, doc = _cabinet(remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST))
    demo_part = part("relay", description="Invented relay")
    demo_item = item("k1", description="Invented relay", part=demo_part.id)
    placement = place("p1", item=demo_item.id, node=c1.id)
    m = model(c1, doc, demo_part, demo_item, placement)
    source(m, doc.id, {})
    assert seen[-1] == (BOM_COLUMNS, ("description", "designations"))

    # Wire label list: only `label` is unbounded (the two ends are compact designations).
    c1, doc = _cabinet(
        add=(K.WIRE_LABEL_LIST,), remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM)
    )
    a_item, a_fn, a_port = pin("p1", "P1")
    b_item, b_fn, b_port = pin("p2", "P2")
    cond = conductor("w1", a=a_port.id, b=b_port.id)
    wf = wire_facet("w1", subject=cond.id, label="W1")
    m = model(c1, doc, a_item, a_fn, a_port, b_item, b_fn, b_port, cond, wf)
    source(m, doc.id, {})
    assert seen[-1] == (WIRE_COLUMNS, ("label",))

    # Designation list: only `description` is unbounded.
    c1, doc = _cabinet(
        add=(K.DESIGNATION_LIST,), remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM)
    )
    demo = item("k1", description="Invented relay")
    m = model(c1, doc, demo)
    source(m, doc.id, {})
    assert seen[-1] == (DESIGNATION_COLUMNS, ("description",))

    # Cable list: `description`, `from_label` and `to_label` are all unbounded (designer's own
    # explicit ruling on this list); the rest (designation, mpn, the three measurements) stay
    # `auto` -- a single designation, a single MPN, plain numbers.
    demo_part = part("cab1", description="Invented 4-core cable")
    cable1 = item("w1", description="Cable one", part=demo_part.id)
    cf1 = cable_facet("w1", subject=cable1.id, length_mm=1500)
    cpf1 = cable_product_facet("w1", subject=demo_part.id)
    m = model(demo_part, cable1, cf1, cpf1)
    cable_list_page(m)
    assert seen[-1] == (CABLE_LIST_COLUMNS, ("description", "from_label", "to_label"))

    # Connector list: only `net` is unbounded (`style` is a catalogue field like MPN, `marking`
    # is a single pin, the rest are single designations).
    c1, doc = _cabinet(
        add=(K.CONNECTOR_LIST,), remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM)
    )
    board_part = part("board1", description="Invented board")
    board = item("jb1", description="Board one", part=board_part.id)
    pcb1 = pcb_facet("board1", subject=board_part.id)
    conn_part, conn_template, conn_fn, conn_facet, conn_ports = connector(
        "j1", item=board.id, name="J1", markings=("1",)
    )
    p1 = place("p1", item=board.id, node=c1.id)
    m = model(
        c1,
        doc,
        board_part,
        board,
        pcb1,
        conn_part,
        conn_template,
        conn_fn,
        conn_facet,
        *conn_ports,
        p1,
    )
    source(m, doc.id, {})
    assert seen[-1] == ((*CONNECTOR_COLUMNS, *PIN_COLUMNS), ("net",))


def test_cable_list_page_renders_two_cables_with_header():
    """Units spec U3: the `system` preset's cable list, one row per top-level cable. Calls
    `cable_list_page` directly, same reason as the BOM test above."""
    demo_part = part("cab1", description="Invented 4-core cable")
    cable1 = item("w1", description="Cable one", part=demo_part.id)
    cf1 = cable_facet("w1", subject=cable1.id, length_mm=1500)
    cpf1 = cable_product_facet("w1", subject=demo_part.id)
    demo_part2 = part("cab2", description="Cable two part")
    cable2 = item("w2", description="Cable two", part=demo_part2.id)
    cf2 = cable_facet("w2", subject=cable2.id, length_mm=None)
    cpf2 = cable_product_facet("w2", subject=demo_part2.id, core_count=0)
    m = model(demo_part, cable1, cf1, cpf1, cable2, cf2, demo_part2, cpf2)
    assert len(cable_list_rows(m)) == _CABLE_LIST_ROW_COUNT
    text = cable_list_page(m)
    for header in (
        "Designation",
        "Mpn",
        "Description",
        "Core count",
        "Gauge mm2",
        "Length mm",
    ):
        assert f'"{header}"' in text
    # This fixture authors no end label on either cable: pdf-0011 does not draw those columns.
    assert '"From label"' not in text
    assert '"To label"' not in text
    # The rendered table, not just the query: one designation cell each, matching the
    # fixture's own row count (the work order's own "exactly your fixture's row count").
    assert text.count('"-W1"') == 1
    assert text.count('"-W2"') == 1


# -- pdf-0011: a column empty in every row is not drawn ---------------------------------------


def _connector_list_model(*, with_net: bool):
    """A cabinet with one board, one two-pin connector; pin `1` is on net `SIG` if `with_net`."""
    c1, doc = _cabinet(
        add=(K.CONNECTOR_LIST,), remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM)
    )
    board_part = part("board1", description="Invented board")
    board = item("jb1", description="Board one", part=board_part.id)
    pcb1 = pcb_facet("board1", subject=board_part.id)
    conn_part, template, fn, facet, ports = connector(
        "j1", item=board.id, name="J1", markings=("1", "2")
    )
    p1 = place("p1", item=board.id, node=c1.id)
    net_key = ("net", "sig")
    nets = (
        (
            Net(
                id=make_id(Net, net_key),
                key=net_key,
                name="SIG",
                net_class=NetClass.SIGNAL,
                ports=(ports[0].id,),
            ),
        )
        if with_net
        else ()
    )
    m = model(c1, doc, board_part, board, pcb1, conn_part, template, fn, facet, *ports, p1, *nets)
    return m, doc


def test_connector_list_without_nets_has_no_net_column_but_keeps_the_rest():
    """Owner ruling 2026-09-24 (pdf-0011): no pin is on a net, so `Net` is not drawn. The other
    filled columns are, and `1fr` (the dropped `net` was the only one) moves to the last."""
    m, doc = _connector_list_model(with_net=False)
    text = source(m, doc.id, {})
    assert '"Net"' not in text
    for header in ("Designation", "Style", "Pincount", "Gender", "Marking"):
        assert f'"{header}"' in text
    # Mate designation and mate port designation are empty too: `Marking` is the last drawn.
    assert "columns: (auto, auto, auto, auto, 1fr)" in text


def test_connector_list_with_a_net_draws_the_net_column():
    m, doc = _connector_list_model(with_net=True)
    text = source(m, doc.id, {})
    assert '"Net"' in text
    assert 'text("SIG")' in text
    assert "columns: (auto, auto, auto, auto, auto, 1fr)" in text


def test_bom_of_part_lines_has_no_revision_column_but_a_unit_line_brings_it():
    """A part line's `revision` is `""`; a `system` BOM's unit line carries the unit's revision."""
    c1, doc = _cabinet(remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST))
    demo_part = part("relay", description="Invented relay")
    demo_item = item("k1", description="Invented relay", part=demo_part.id)
    m = model(c1, doc, demo_part, demo_item, place("p1", item=demo_item.id, node=c1.id))
    part_only = bom_page(m, documents(m)[doc.id])
    assert '"Mpn"' in part_only
    assert '"Revision"' not in part_only

    u = unit("u1", name="relay-interface-board")
    system_doc = document("d2", preset=DocumentPreset.SYSTEM, cover="# Cover", notes=None)
    m2 = model(u, system_doc)
    with_unit_line = bom_page(m2, documents(m2)[system_doc.id])
    assert '"Revision"' in with_unit_line
    assert 'text("1.1")' in with_unit_line


def _strip_model(*, jumper: bool):
    """A cabinet strip `X1` of two bridged terminals; a jumper joins them if `jumper`, and
    terminal T:1 also has a wire to `K1:A1` either way (so Internal ends is never empty)."""
    c1, doc = _cabinet(remove=(K.PLC_LIST, K.SCHEMATIC, K.BOM))
    strip = item("x1", description="Strip one")
    t1, t1_facet, t1_fn, t1_port = bridged_terminal("t1", strip=strip.id, group="T", index=1)
    t2, t2_facet, t2_fn, t2_port = bridged_terminal("t2", strip=strip.id, group="T", index=2)
    far_item, far_fn, far_port = pin("far", "K1:A1")
    wire = conductor("w1", a=t1_port.id, b=far_port.id)
    jumpers = (conductor("j1", a=t1_port.id, b=t2_port.id, kind=ConductorKind.JUMPER),)
    p1 = place("p1", item=strip.id, node=c1.id)
    m = model(
        c1,
        doc,
        strip,
        t1,
        t1_facet,
        t1_fn,
        t1_port,
        t2,
        t2_facet,
        t2_fn,
        t2_port,
        far_item,
        far_fn,
        far_port,
        wire,
        *(jumpers if jumper else ()),
        p1,
    )
    return m, doc


def test_terminal_list_strip_with_a_jumper_group_draws_the_bridge_column():
    m, doc = _strip_model(jumper=True)
    text = source(m, doc.id, {})
    assert '"Bridge"' in text
    # Side B is empty and dropped; Side A keeps its `1fr`, Bridge its 15mm.
    assert "columns: (auto, auto, auto, 1fr, 15mm)" in text
    assert '"Side B"' not in text


def _two_sided_strip_model():
    """Strip `X01`: T:1-T:3 bridged (a jumper on the internal side, one on the external side),
    and T:4 wired to `K1:A1` (internal) and `K2:B1` (external). Every terminal has both ports."""
    c1, doc = _cabinet(remove=(K.PLC_LIST, K.SCHEMATIC, K.BOM))
    strip = item("x01", description="Strip one")
    records = []
    ports = {}
    for number in (1, 2, 3, 4):
        key = f"t{number}"
        child, facet, fn, internal = bridged_terminal(key, strip=strip.id, group="T", index=number)
        external = external_port(key)
        ports[number] = (internal, external)
        records.extend((child, facet, fn, internal, external))
    k1, k1_fn, k1_port = pin("k1", "K1:A1")
    k2, k2_fn, k2_port = pin("k2", "K2:B1")
    conductors_ = (
        conductor("j1", a=ports[1][0].id, b=ports[2][0].id, kind=ConductorKind.JUMPER),
        conductor("j2", a=ports[2][1].id, b=ports[3][1].id, kind=ConductorKind.JUMPER),
        conductor("w1", a=ports[4][0].id, b=k1_port.id),
        conductor("w2", a=ports[4][1].id, b=k2_port.id),
    )
    p1 = place("p1", item=strip.id, node=c1.id)
    m = model(c1, doc, strip, *records, k1, k1_fn, k1_port, k2, k2_fn, k2_port, *conductors_, p1)
    return m, doc


def _cell_parts(text: str) -> list[str]:
    """Every `; `-separated part of every `text("...")` cell in `text`, headers included."""
    return [part for cell in re.findall(r'text\("([^"]*)"\)', text) for part in cell.split("; ")]


def test_terminal_list_headers_are_side_a_and_side_b():
    """Owner ruling 2026-09-24 (item 4): the ends columns are headed Side A / Side B."""
    m, doc = _two_sided_strip_model()
    text = source(m, doc.id, {})
    assert '"Side A"' in text
    assert '"Side B"' in text
    assert '"Internal ends"' not in text
    assert '"External ends"' not in text


def test_terminal_list_no_jumper_partner_in_either_ends_column():
    """T2 amended: the Bridge column shows a jumper, so its partner is in neither ends column
    (T:1's and T:2's partner on the internal side, T:2's and T:3's on the external side). A real
    wire's far end stays on both sides, so the test cannot pass by emptiness."""
    m, doc = _two_sided_strip_model()
    parts = _cell_parts(source(m, doc.id, {}))
    # A terminal's port and its own designation cell read alike (`-X01:T:n`), so a partner
    # showing up in an ends column would make its designation appear a second time.
    for number in (1, 2, 3):
        assert parts.count(f"-X01:T:{number}") == 1
    assert "-K1:A1:1" in parts  # T:4's real wire, Side A
    assert "-K2:B1:1" in parts  # T:4's real wire, Side B


_PT_PER_MM = 72 / 25.4


def _column_widths_mm(svg: str) -> list[float]:
    """The compiled table's column widths (mm), from its full-height vertical strokes.

    Typst's SVG draws each column border as `<path transform="translate(x y)" d="M 0 0v h"/>`
    (x in pt). The table's own borders are the verticals of the greatest height; the shorter
    ones are the Bridge column's marks.
    """
    lines = [
        (float(x), float(y), float(h))
        for x, y, h in re.findall(
            r'transform="translate\(([\d.]+) ([\d.]+)\)" d="M 0 0v ([\d.]+)"', svg
        )
    ]
    tallest = max(h for _x, _y, h in lines)
    xs = sorted(x for x, _y, h in lines if h == tallest)
    return [(right - left) / _PT_PER_MM for left, right in pairwise(xs)]


def test_terminal_list_side_a_and_side_b_compile_equally_wide():
    """Owner ruling 2026-09-24 (pdf-0011 F1): Side A and Side B are `1fr` of equal weight. Read
    off the compiled page, not the source: a strip with content in both, every column drawn
    (Designation, Group, Index, Side A, Side B, Bridge), Side A and Side B within 0.5 mm.
    Can-fail: Side B back to `auto` leaves Side A 90.9 mm wider than Side B.
    """
    m, _doc = _two_sided_strip_model()
    (strip,) = terminal_strips(m)
    table = _terminal_table(m, terminal_rows(m, strip))
    page = (
        "#set page(width: 210mm, height: 100mm, margin: 15mm)\n"
        '#set text(font: "Liberation Serif", size: 9pt)\n' + table
    )
    widths = _column_widths_mm(typst.compile(page.encode("utf-8"), format="svg").decode("utf-8"))
    assert len(widths) == 6
    side_a, side_b, bridge = widths[3], widths[4], widths[5]
    assert abs(bridge - 15) < 0.5
    assert side_a > 30
    assert abs(side_a - side_b) < 0.5


def test_terminal_list_strip_without_a_jumper_group_has_no_bridge_column():
    m, doc = _strip_model(jumper=False)
    text = source(m, doc.id, {})
    assert '"Bridge"' not in text
    assert "table.cell(inset: 0pt" not in text  # no Bridge cell either, not just no header
    assert "columns: (auto, auto, auto, 1fr)" in text  # Internal ends stays the `1fr`


def test_table_drops_an_empty_wide_column_and_the_last_column_takes_1fr():
    """Pdf-0011 fallback: `c` (the only wide column) is empty, so `b`, now last, is `1fr`."""
    text = _lists._table(("a", "b", "c"), [("x", "y", ""), ("z", "w", None)], ("c",))
    assert 'strong(text("C"))' not in text
    assert 'strong(text("A")), strong(text("B"))' in text
    assert "columns: (auto, 1fr)" in text


def test_table_keeps_an_existing_wide_column_when_it_survives():
    text = _lists._table(("a", "b", "c"), [("", "y", "v")], ("b",))
    assert "columns: (1fr, auto)" in text
    assert 'strong(text("A"))' not in text


def test_table_with_only_blank_rows_draws_nothing_and_does_not_crash():
    """Every cell of every row blank: no column is left, so no table; no rows too (pdf-0019)."""
    assert _lists._table(("a", "b"), [("", None)], ("b",)) == ""
    assert _lists._table(("a", "b"), [], ("b",)) == ""


# -- model-0054 sections 4 and 5: ends in the document's context, headings signed -------------


def _context_ends_model(*, unit_document: bool, add=()):
    """Strip `X3` at `C1`, its terminal `T:1` wired inside to `B12:2/T1` (also at `C1`, labelled
    `W1`) and outside to `M1:U1` (at a location `EXT`, labelled `W2`).

    The document is a location document about `C1`, or (`unit_document`) a unit document about
    a unit the strip and `B12` belong to, which has no location of its own.
    """
    c1 = location("C1", "Demo cabinet")
    ext = location("EXT", "Outside the cabinet")
    u = unit("u1", name="pump-cabinet") if unit_document else None
    remove = (K.SCHEMATIC, K.PLC_LIST, K.BOM)
    if u is None:
        doc = document(
            "d1",
            preset=DocumentPreset.CABINET_SCHEMATIC,
            subject=c1,
            cover="# Cover",
            notes=None,
            add=add,
            remove=remove,
        )
    else:
        doc = _unit_document(u, add=add, remove=remove)
    strip = item("x3", description="Strip three", unit=None if u is None else u.id)
    child, facet, fn, internal = bridged_terminal("t1", strip=strip.id, group="T", index=1)
    external = external_port("t1")
    b12, b12_fn, b12_port = pin("b12", "B12", unit=None if u is None else u.id)
    m1, m1_fn, m1_port = pin("m1", "M1")
    b12_port = replace(b12_port, name="2/T1")
    m1_port = replace(m1_port, name="U1")
    w1 = conductor("w1", a=internal.id, b=b12_port.id)
    w2 = conductor("w2", a=external.id, b=m1_port.id)
    labels = (
        wire_facet("w1", subject=w1.id, label="W1"),
        wire_facet("w2", subject=w2.id, label="W2"),
    )
    places = (
        place("p-strip", item=strip.id, node=c1.id),
        place("p-b12", item=b12.id, node=c1.id),
        place("p-m1", item=m1.id, node=ext.id),
    )
    records = (c1, ext, doc, strip, child, facet, fn, internal, external)
    records += (b12, b12_fn, b12_port, m1, m1_fn, m1_port, w1, w2, *labels, *places)
    return model(*records, *([] if u is None else [u])), doc


def test_terminal_list_prints_an_inside_end_short_and_an_outside_end_with_its_location():
    """Item 5: in one row, the end inside the document's own location `C1` is short, the one at
    `EXT` carries its location path. Can-fail: dropping `context=` from `terminal_rows_for` makes
    the outside end read `-M1:U1` (probe run, Edit-and-restore)."""
    m, doc = _context_ends_model(unit_document=False)
    text = source(m, doc.id, {})
    assert 'box(text("-B12:2/T1")), box(text("+EXT-M1:U1"))' in text


def test_terminal_list_of_a_unit_document_uses_the_strips_own_location_as_context():
    """A unit document has no location; the strip's own (`C1`) is the context, so the unit's own
    `B12` prints short and the outside `M1` its whole path (model-0143).
    Can-fail: removing the `item_location` fallback in `_list_context` leaves no context, and
    `B12` reads `+C1-B12:2/T1`."""
    m, doc = _context_ends_model(unit_document=True)
    assert documents(m)[doc.id].location is None
    text = source(m, doc.id, {})
    assert 'box(text("-B12:2/T1")), box(text("+EXT-M1:U1"))' in text


def test_terminal_and_connector_list_headings_carry_their_sign():
    """Item 8: the strip and board headings read `-X3` / `-JB1`, not the bare tag. Can-fail:
    `item_designation` in either heading prints `X3` / `JB1`."""
    m, doc = _context_ends_model(unit_document=False)
    assert '#heading(level: 2, text("-X3"))' in source(m, doc.id, {})
    m, doc = _connector_list_model(with_net=False)
    assert '#heading(level: 2, text("-JB1"))' in source(m, doc.id, {})


def test_wire_label_list_of_a_location_document_prefixes_an_outside_end():
    """Item 5 for the wire-label list: `W1` ends inside `C1` (short both sides), `W2` ends at
    `EXT`. Can-fail: dropping `context=` from `wire_rows_for` makes the `W2` wire end `-M1:U1`."""
    m, doc = _context_ends_model(unit_document=False, add=(K.WIRE_LABEL_LIST,))
    text = source(m, doc.id, {})
    assert 'text("-X3:T:1"), text("-B12:2/T1"), text("black")' in text
    assert 'text("-X3:T:1"), text("+EXT-M1:U1"), text("black")' in text  # the fixed end order (V8)


def _plc_context_model(*, unit_document: bool):
    """Module `MOD1`: channel 1 wired to `B12` at `C1`, channel 2 to `M1` at `EXT`.

    The document is a location document about `C1` (`MOD1` is placed at `C1`), or
    (`unit_document`) a unit document about the unit `MOD1` belongs to, which has no location
    of its own and, `MOD1` being unplaced, no placement location either (model-0056).
    """
    c1 = location("C1", "Demo cabinet")
    ext = location("EXT", "Outside the cabinet")
    u = unit("u1", name="pump-cabinet") if unit_document else None
    remove = (K.SCHEMATIC, K.TERMINAL_LIST, K.BOM)
    if u is None:
        doc = document(
            "d1",
            preset=DocumentPreset.CABINET_SCHEMATIC,
            subject=c1,
            cover="# Cover",
            notes=None,
            remove=remove,
        )
    else:
        doc = _unit_document(u, remove=remove)
    module = item("mod1", description="PLC module", unit=None if u is None else u.id)
    parts = []
    ports = []
    for number in (1, 2):
        module_part, template, fn, facet = plc_channel(
            f"ch{number}",
            module=module.id,
            name=f"ch{number}",
            signal=SignalType.DI,
            channel=number,
        )
        key = ("port", f"ch{number}")
        ports.append(
            Port(
                id=make_id(Port, key),
                key=key,
                function=fn.id,
                template=None,
                name="1",
                role=PortRole.GENERIC,
            )
        )
        parts += [module_part, template, fn, facet]
    b12, b12_fn, b12_port = pin("b12", "B12")
    m1, m1_fn, m1_port = pin("m1", "M1")
    wires = (
        conductor("w1", a=ports[0].id, b=b12_port.id),
        conductor("w2", a=ports[1].id, b=m1_port.id),
    )
    places = (
        place("p-b12", item=b12.id, node=c1.id),
        place("p-m1", item=m1.id, node=ext.id),
        *([place("p-mod1", item=module.id, node=c1.id)] if u is None else []),
    )
    records = (c1, ext, doc, module, *parts, *ports, b12, b12_fn, b12_port, m1, m1_fn, m1_port)
    return model(*records, *wires, *places, *([] if u is None else [u])), doc


def test_plc_list_of_a_location_document_prefixes_an_outside_end():
    """The PLC list of a location document reads its ends in that location: `B12` at `C1` is
    short, `M1` at `EXT` carries its location path. Can-fail: dropping `context=` from
    `plc_channel_rows_for` makes the second end read `-M1:1` (probe run, Edit-and-restore)."""
    m, doc = _plc_context_model(unit_document=False)
    text = source(m, doc.id, {})
    assert 'text("-MOD1:1"), text("di"), text("-B12:1")' in text
    assert 'text("-MOD1:2"), text("di"), text("+EXT-M1:1")' in text


def test_plc_list_of_a_unit_document_has_no_location_context():
    """A unit document has no location (`record.location is None`) and, its unit unplaced, no
    placement location: no end is short, `B12` at `C1` prints its full path too. Can-fail:
    passing `C1` as the context in `plc_channel_rows_for` makes `B12` end `-B12:1`."""
    m, doc = _plc_context_model(unit_document=True)
    assert documents(m)[doc.id].location is None
    text = source(m, doc.id, {})
    assert 'text("-MOD1:1"), text("di"), text("+C1-B12:1")' in text
    assert 'text("-MOD1:2"), text("di"), text("+EXT-M1:1")' in text


def test_connector_list_prints_a_mate_pin_outside_the_documents_location_with_its_location():
    """Item 5 for the connector list: board `JB1` at `C1` has `J1` mated to `H1` at `EXT` and `J2`
    mated to `H2` at `C1`. The `EXT` mate pin carries its location path, the `C1` one is short.
    Can-fail: dropping `context=` from `connector_rows_for` makes the first read `-H1:1`."""
    c1, doc = _cabinet(
        add=(K.CONNECTOR_LIST,), remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM)
    )
    ext = location("EXT", "Outside the cabinet")
    board_part = part("board1", description="Invented board")
    board = item("jb1", description="Board one", part=board_part.id)
    pcb1 = pcb_facet("board1", subject=board_part.id)
    h1 = item("h1", description="Housing outside")
    h2 = item("h2", description="Housing inside")
    j1 = connector("j1", item=board.id, name="J1", markings=("1",))
    j2 = connector("j2", item=board.id, name="J2", markings=("1",))
    p1 = connector("p1", item=h1.id, name="P1", markings=("1",))
    p2 = connector("p2", item=h2.id, name="P2", markings=("1",))
    mates = tuple(
        Mate(id=make_id(Mate, (key,)), key=(key,), a=a[2].id, b=b[2].id)
        for key, a, b in (("m1", j1, p1), ("m2", j2, p2))
    )
    places = (
        place("p-jb1", item=board.id, node=c1.id),
        place("p-h1", item=h1.id, node=ext.id),
        place("p-h2", item=h2.id, node=c1.id),
    )
    parts = [rec for group in (j1, j2, p1, p2) for rec in (*group[:4], *group[4])]
    m = model(c1, ext, doc, board_part, board, pcb1, h1, h2, *parts, *mates, *places)
    text = source(m, doc.id, {})
    assert 'text("+EXT-H1:1")' in text
    assert 'text("-H2:1")' in text
    assert 'text("-H1:1")' not in text


# -- document_unit's `unit_name` path: the only way `model` is actually read (mutmut rank 6) ---


def _unit_name_document(name, *, add=(), remove=()):
    """A `CABINET_SCHEMATIC` document about `name`, resolved through `unit_name` (spec UN1/UN2),
    never through the `unit` field -- `document()` has no `unit_name=` of its own, so this
    builds a document about a throwaway location (`Document.__post_init__` demands exactly one
    subject at construction, so `subject=None` alone would raise immediately) and then, in one
    `replace`, drops that location and sets `unit_name` instead -- still exactly one subject.
    Unlike `.unit`, resolving `.unit_name` makes `document_unit` genuinely read `model` (via
    `units_named`), which is what these three tests are about."""
    throwaway = location("C0", "Unused, replaced by unit_name below")
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=throwaway,
        cover="# Cover",
        notes=None,
        add=add,
        remove=remove,
    )
    return replace(doc, location=None, unit_name=name)


def test_plc_channel_rows_for_resolves_the_documents_unit_by_name():
    """`plc_channel_rows_for` reads `document_unit(model, record)`, and a `unit_name`-resolved
    document is the only shape that makes `document_unit` actually consult `model` (it calls
    `units_named(model, ...)`; the `.unit` field never touches `model` at all). Can-fail
    (mutmut): `document_unit(None, record)` crashes inside `units_named` reading `None`'s
    tables, instead of resolving to `u`'s id and keeping only `MOD1`'s channel."""
    u = unit("u1", name="pump-cabinet")
    doc = _unit_name_document("pump-cabinet", remove=(K.SCHEMATIC, K.TERMINAL_LIST, K.BOM))
    mod_in = item("mod1", description="PLC module", unit=u.id)
    mod_out = item("mod2", description="Other module")
    part_in, tmpl_in, fn_in, facet_in = plc_channel(
        "ch1", module=mod_in.id, name="ch1", signal=SignalType.DI, channel=1
    )
    part_out, tmpl_out, fn_out, facet_out = plc_channel(
        "ch2", module=mod_out.id, name="ch2", signal=SignalType.DI, channel=1
    )
    m = model(
        u,
        doc,
        mod_in,
        mod_out,
        part_in,
        tmpl_in,
        fn_in,
        facet_in,
        part_out,
        tmpl_out,
        fn_out,
        facet_out,
    )
    record = documents(m)[doc.id]
    # Confirms the by-name resolution genuinely happened (the `units_named` branch), not the
    # dead `.unit` shortcut -- `record.unit` is `None` here, only `record.unit_name` is set.
    assert document_unit(m, record) == u.id
    rows = plc_channel_rows_for(m, record)
    assert {row.channel_designation for row in rows} == {"-MOD1:1"}  # MOD2 stays out


def test_wire_rows_for_resolves_the_documents_unit_by_name():
    """Same shape for `wire_rows_for`. Can-fail (mutmut): `document_unit(None, record)`
    crashes the same way, instead of resolving to `u`'s id and keeping only `WIN`."""
    u = unit("u1", name="pump-cabinet")
    doc = _unit_name_document(
        "pump-cabinet", add=(K.WIRE_LABEL_LIST,), remove=(K.SCHEMATIC, K.TERMINAL_LIST, K.BOM)
    )
    a_in, fn_a_in, port_a_in = pin("a_in", "A1", unit=u.id)
    b_in, fn_b_in, port_b_in = pin("b_in", "B1", unit=u.id)
    cond_in = conductor("w_in", a=port_a_in.id, b=port_b_in.id)
    wf_in = wire_facet("w_in", subject=cond_in.id, label="WIN")
    a_out, fn_a_out, port_a_out = pin("a_out", "A2")
    b_out, fn_b_out, port_b_out = pin("b_out", "B2")
    cond_out = conductor("w_out", a=port_a_out.id, b=port_b_out.id)
    wf_out = wire_facet("w_out", subject=cond_out.id, label="WOUT")
    m = model(
        u,
        doc,
        a_in,
        fn_a_in,
        port_a_in,
        b_in,
        fn_b_in,
        port_b_in,
        cond_in,
        wf_in,
        a_out,
        fn_a_out,
        port_a_out,
        b_out,
        fn_b_out,
        port_b_out,
        cond_out,
        wf_out,
    )
    record = documents(m)[doc.id]
    assert document_unit(m, record) == u.id
    rows = wire_rows_for(m, record)
    assert {row.conductor for row in rows} == {cond_in.id}  # w_out (no unit) stays out


def test_connector_rows_for_resolves_the_documents_unit_by_name():
    """Same shape for `connector_rows_for`, but the fixture must tell `unit=u.id` apart from a
    dropped/defaulted `unit=None` too (mutmut ids 3 and 7 never call `document_unit` at all --
    they drop the argument or the keyword, so the id-9/plc/wire crash-on-`None`-model probe
    above does not touch them). `board` is the *sole* root item of `u` (units spec UNIT-ID I4)
    with two connectors, so `connector_designation`'s `is_own_unit_root` branch fires only when
    `unit` genuinely reaches it: `-J1` (the root's own tag dropped) with the real `unit=u.id`,
    versus `-JB1-J1` with `unit=None` -- can-fail, verified below by calling the real
    `connector_rows` with `unit=` omitted and confirming it gives the *other* string.
    """
    u = unit("u1", name="pump-cabinet")
    doc = _unit_name_document(
        "pump-cabinet",
        add=(K.CONNECTOR_LIST,),
        remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    board_part = part("board1", description="Invented board")
    board = item("jb1", description="Board one", part=board_part.id, unit=u.id)
    pcb1 = pcb_facet("board1", subject=board_part.id)
    conn1_part, conn1_template, conn1_fn, conn1_facet, conn1_ports = connector(
        "j1", item=board.id, name="J1", markings=("1",)
    )
    conn2_part, conn2_template, conn2_fn, conn2_facet, conn2_ports = connector(
        "j2", item=board.id, name="J2", markings=("1",)
    )
    m = model(
        u,
        doc,
        board_part,
        board,
        pcb1,
        conn1_part,
        conn1_template,
        conn1_fn,
        conn1_facet,
        *conn1_ports,
        conn2_part,
        conn2_template,
        conn2_fn,
        conn2_facet,
        *conn2_ports,
    )
    record = documents(m)[doc.id]
    assert document_unit(m, record) == u.id
    rows = connector_rows_for(m, record, board.id)
    assert len(rows) == 2
    j1_row = next(row for row in rows if row.connector == conn1_fn.id)
    assert j1_row.designation == "-J1"  # the unit's own sole root: no `-JB1-` prefix


# -- mutmut kernel triage: `_boards_for`'s LOCATION branch sort key (ids 19/21/22) -------------


def test_boards_for_location_branch_orders_by_designation_not_by_raw_id():
    """`_boards_for`'s LOCATION branch (the last `return`, line 620) sorts boards by
    `(item_designation(model, board), board)`, not by the boards' raw `Id`s. `Id` orders by an
    opaque uuid5 hash of the authoring key (kernel/ids.py), unrelated to the designation string
    it hashes from -- so a sort that drops the `item_designation` key and falls back to
    `sorted(selected)` need not agree with the correct order. `JBA` and `JBB` are picked because
    their raw-`Id` order is the *reverse* of their designation order (confirmed empirically
    below, not assumed): mutmut ids 19 (`key=None`) and 21 (no `key` at all) would then return
    the boards in the wrong order, and id 22 (`key=lambda board: None`) crashes outright sorting
    two items with an all-equal key -- all three fail this test.
    """
    c1, doc = _cabinet(
        add=(K.CONNECTOR_LIST,), remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM)
    )
    board_a_part = part("boarda", description="Board A")
    board_a = item("jba", description="Board A", part=board_a_part.id)
    pcb_a = pcb_facet("boarda", subject=board_a_part.id)
    board_b_part = part("boardb", description="Board B")
    board_b = item("jbb", description="Board B", part=board_b_part.id)
    pcb_b = pcb_facet("boardb", subject=board_b_part.id)
    p_a = place("pa", item=board_a.id, node=c1.id)
    p_b = place("pb", item=board_b.id, node=c1.id)
    m = model(c1, doc, board_a_part, board_a, pcb_a, board_b_part, board_b, pcb_b, p_a, p_b)
    record = documents(m)[doc.id]
    raw_order = tuple(sorted([board_a.id, board_b.id]))
    designation_order = tuple(
        sorted([board_a.id, board_b.id], key=lambda board: item_designation(m, board))
    )
    # The fixture's own discriminating power: the two orders genuinely disagree, so a sort that
    # fell back to raw `Id`s could not coincidentally pass the assertion below.
    assert raw_order != designation_order
    assert designation_order == (board_a.id, board_b.id)
    assert _lists._boards_for(m, record) == designation_order


def test_strip_description_prints_in_the_terminal_list_heading_and_designations_list():
    c1, doc = _cabinet(remove=(K.SCHEMATIC, K.PLC_LIST, K.BOM))
    strip = item("x1", description="valve supply")
    t1, t1_facet = terminal("t1", strip=strip.id, group="L", index=1)
    m = model(c1, doc, strip, t1, t1_facet, place("p1", item=strip.id, node=c1.id))
    assert 'text("valve supply")' in source(m, doc.id, {})
    assert [r.description for r in designation_list(m) if r.designation == "-X1"] == [
        "valve supply"
    ]


def test_terminal_table_with_no_rows_is_empty_so_its_strip_section_is_dropped():
    """A strip with no rows has no table, and `terminal_list_page` drops its whole section."""
    c1, doc = _cabinet(remove=(K.SCHEMATIC, K.PLC_LIST, K.BOM))
    m = model(c1, doc)
    assert _lists._terminal_table(m, ()) == ""
    assert terminal_list_page(m, documents(m)[doc.id]) == ""
