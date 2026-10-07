"""`source`: page geometry, cover and notes (spec P4, P5, P10). Determinism is Part 5."""

from _build import (
    cable_facet,
    cable_product_facet,
    conductor,
    core_facet,
    document,
    drawing_set,
    item,
    layout_page,
    location,
    model,
    part,
    pin,
    place,
    project,
    revision_entry,
    sheet_format,
    unit,
)
from fransys_pdf import source
from fransys_pdf._drawings import harness_cables_for, schematic_pages
from fransys_pdf._geometry import (
    document_facts,
    document_heading,
    project_facts,
    resolve_sheet_format,
    subject_label,
)
from fransys_pdf._pages import cover_page

from fransys_model.derive.cable_drawing import cable_block_key
from fransys_model.kernel.ids import render_id
from fransys_model.vocab import ConductorKind, DocumentPreset, PageKind, documents

K = PageKind

# Part 1 (unit documents): named non-zero counts for the two-drawing-set fixtures below.
_UNIT_DOCUMENT_PAGE_COUNT = 2


def _cabinet(**overrides):
    c1 = location("C1", "Demo cabinet")
    p = project()
    doc = document(
        "d1",
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=c1,
        cover="# Cabinet cover\n\nSome cover text.",
        notes=overrides.pop("notes", "Some notes."),
        remove=overrides.pop("remove", (K.CONTENTS, K.HARNESS_DRAWING, K.BOM)),
    )
    return model(c1, p, doc), doc


def test_cover_and_notes_pages_are_separated_by_a_page_break():
    m, doc = _cabinet()
    text = source(m, doc.id, {})
    assert text.count("#pagebreak()") == 1


def test_cover_has_no_facts_table_but_keeps_its_own_heading_and_text():
    """R10 (owner's appearance pass): the cover drops the six `Project` facts as a table; the
    title block (page-frame R3) already carries them on every page, the cover included. Paired
    absence/presence on `cover_page` alone, not the whole `source()`, so a blank cover cannot
    pass this check by accident -- the whole document still contains the facts through the
    title block in the page background."""
    m, doc = _cabinet()
    text = cover_page(m, doc)
    assert "#table" not in text  # absence: no fact table of any shape
    assert '"DEMO-1"' not in text  # absence: Project.number, only in the title block now
    assert '"Demo Co"' not in text  # absence: Project.customer, likewise
    assert '#heading(level: 1, text("Cabinet cover"))' in text  # presence: the cover's own heading
    assert '"Some cover text."' in text  # presence: the cover's own text
    assert "Harness drawing" in text  # presence: preset words, part of the document heading
    assert "C1 Demo cabinet" in text  # presence: subject label, part of the document heading


def test_cover_markdown_is_rendered():
    m, doc = _cabinet()
    text = source(m, doc.id, {})
    assert '#heading(level: 1, text("Cabinet cover"))' in text
    assert '"Some cover text."' in text


def test_no_notes_page_when_there_is_no_notes_text():
    m, doc = _cabinet(notes=None)
    text = source(m, doc.id, {})
    assert '"Notes"' not in text
    assert text.count("#pagebreak()") == 0


def test_house_sheet_when_the_document_has_no_drawing_pages():
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        notes=None,
        remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    m = model(c1, doc)
    sheet = resolve_sheet_format(m, documents(m)[doc.id], (K.COVER,))
    assert (sheet.width_mm, sheet.height_mm) == (420, 297)


def test_schematic_pages_are_inlined_in_number_order_when_every_key_is_present():
    c1 = location("C1", "Demo cabinet")
    ds = drawing_set("ds1", location=c1)
    p1 = layout_page("p1", drawing_set=ds, number=1)
    p2 = layout_page("p2", drawing_set=ds, number=2)
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        notes=None,
        remove=(K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    m = model(c1, ds, p2, p1, doc)  # inserted out of number order: proves the sort, not insertion
    svgs = {
        render_id(p1.id): "<svg>one</svg>",
        render_id(p2.id): "<svg>two</svg>",
    }
    text = source(m, doc.id, svgs)
    assert text.count("#page(margin: 0mm, background:") == 2  # page-frame R1, R4: full bleed
    assert text.index("<svg>one</svg>") < text.index("<svg>two</svg>")
    assert text.count("#pagebreak()") == 2  # COVER|SCHEMATIC, then between the two SCHEMATIC pages
    # R3's sheet counter (`n / N` within the drawing set) is its own number, not the document
    # counter: page 1's cell reads "1 / 2", page 2's reads "2 / 2", each in its own block.
    assert 'text(size: 10pt, text("1 / 2"))' in text
    assert 'text(size: 10pt, text("2 / 2"))' in text


def test_schematic_pages_fall_back_to_no_drawings_when_one_key_is_missing():
    c1 = location("C1", "Demo cabinet")
    ds = drawing_set("ds1", location=c1)
    p1 = layout_page("p1", drawing_set=ds, number=1)
    p2 = layout_page("p2", drawing_set=ds, number=2)
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        notes=None,
        remove=(K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    m = model(c1, ds, p1, p2, doc)
    svgs = {render_id(p1.id): "<svg>one</svg>"}
    text = source(m, doc.id, svgs)
    assert text.count('#par(text("No drawings."))') == 1
    assert "<svg>" not in text


def test_schematic_pages_fall_back_to_no_drawings_when_the_location_has_no_drawing_set():
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        notes=None,
        remove=(K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    m = model(c1, doc)
    text = source(m, doc.id, {})
    assert '#par(text("No drawings."))' in text


def test_schematic_pages_fall_back_to_no_drawings_for_an_item_subject():
    board = item("a1", description="Invented board")
    doc = document(
        "d1",
        preset=DocumentPreset.PCB_SCHEMATIC,
        subject=board,
        cover="# Cover",
        notes=None,
        remove=(K.CONNECTOR_LIST, K.BOM),
    )
    m = model(board, doc)
    text = source(m, doc.id, {})
    assert '#par(text("No drawings."))' in text


def test_location_document_picks_only_the_unit_none_set_at_its_location():
    """The join-key fix (model-0041 amending decision 0024, units spec U1): a location subject
    matches `unit is None` at that location, never a nested unit's own set that happens to
    share the location node. `ds_nested`'s `number` (1) sorts before `ds_top`'s (2) on
    purpose: the old `min(..., key=number)` body, filtering by location alone, would have
    picked `ds_nested` -- the live bug this test proves fixed.
    """
    c1 = location("C1", "Demo cabinet")
    u = unit("u1", name="nested-unit")
    ds_nested = drawing_set("ds_nested", location=c1, unit=u, number=1)
    ds_top = drawing_set("ds_top", location=c1, number=2)
    p_nested = layout_page("p_nested", drawing_set=ds_nested, number=1)
    p_top = layout_page("p_top", drawing_set=ds_top, number=1)
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        notes=None,
        remove=(K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    m = model(c1, u, ds_nested, ds_top, p_nested, p_top, doc)
    record = documents(m)[doc.id]
    pages = schematic_pages(m, record, (K.SCHEMATIC,))
    assert [page.id for page in pages] == [p_top.id]


def test_unit_document_gets_pages_from_every_one_of_its_units_sets_in_location_order():
    """A unit document's schematic pages span every drawing set of its unit, any location,
    sorted by the sets' own `number` (layout-0045: unit-then-location order), then page
    number within each set (units spec U3's "in location order" for `cabinet_schematic` with
    a unit)."""
    c1 = location("C1", "First cabinet")
    c2 = location("C2", "Second cabinet")
    u = unit("u1", name="pump-cabinet")
    ds1 = drawing_set("ds1", location=c1, unit=u, number=1)
    ds2 = drawing_set("ds2", location=c2, unit=u, number=2)
    p1 = layout_page("p1", drawing_set=ds1, number=1)
    p2 = layout_page("p2", drawing_set=ds2, number=1)
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=u,
        cover="# Cover",
        notes=None,
        remove=(K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    m = model(c1, c2, u, ds1, ds2, p1, p2, doc)
    record = documents(m)[doc.id]
    pages = schematic_pages(m, record, (K.SCHEMATIC,))
    assert len(pages) == _UNIT_DOCUMENT_PAGE_COUNT
    assert [page.id for page in pages] == [p1.id, p2.id]


def test_unit_document_source_wires_title_block_scope_and_per_set_counter():
    """Integration proof, end to end through `source()`'s own `schematic_source` section, not
    the lower-level functions alone: `document_facts`' unit revision/date (Part 2), the
    unit-name scope cell (`subject_label`), and the per-drawing-set `n / N` counter (a bug
    only reachable once a unit document can span more than one set, Part 1's own capability).
    Two drawing sets of one page each, so a document-wide `len(pages_found)` counter (the old
    body) would wrongly print `1 / 2` on each page instead of `1 / 1`.
    """
    c1 = location("C1", "First cabinet")
    c2 = location("C2", "Second cabinet")
    u = unit("u1", name="pump-cabinet", revision=1)
    r1 = revision_entry("r1", unit=u, revision=1, date="2026-09-01", text="First release")
    r2 = revision_entry("r2", unit=u, revision=2, date="2026-09-23", text="Later")
    p = project(revision=9)
    rp = revision_entry("rp", unit=None, revision=9, date="2020-01-01")
    ds1 = drawing_set("ds1", location=c1, unit=u, number=1)
    ds2 = drawing_set("ds2", location=c2, unit=u, number=2)
    page1 = layout_page("p1", drawing_set=ds1, number=1)
    page2 = layout_page("p2", drawing_set=ds2, number=1)
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=u,
        cover="# Cover",
        notes=None,
        remove=(K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    m = model(c1, c2, u, r1, r2, p, rp, ds1, ds2, page1, page2, doc)
    svgs = {render_id(page1.id): "<svg>one</svg>", render_id(page2.id): "<svg>two</svg>"}
    text = source(m, doc.id, svgs)
    assert '"2026-09-01"' in text  # the unit's own current revision date
    assert '"2020-01-01"' not in text  # never Project's
    assert text.count('"1 / 1"') == 2  # each page's own set, not the document-wide total
    assert '"1 / 2"' not in text
    assert '"pump-cabinet"' in text  # the scope cell


def test_sheet_format_of_the_locations_drawing_set_when_schematic_pages_are_requested():
    c1 = location("C1", "Demo cabinet")
    fmt = sheet_format("a4", width_mm=210, height_mm=297)
    ds = drawing_set("ds1", location=c1)
    page = layout_page("p1", drawing_set=ds, number=1, sheet_format=fmt)
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        notes=None,
        remove=(K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    m = model(c1, fmt, ds, page, doc)
    record = documents(m)[doc.id]
    resolved = resolve_sheet_format(m, record, (K.COVER, K.SCHEMATIC))
    assert (resolved.width_mm, resolved.height_mm) == (210, 297)


def test_house_sheet_when_the_drawing_sets_first_page_names_no_sheet_format():
    c1 = location("C1", "Demo cabinet")
    ds = drawing_set("ds1", location=c1)
    page = layout_page("p1", drawing_set=ds, number=1, sheet_format=None)
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        notes=None,
        remove=(K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    m = model(c1, ds, page, doc)
    record = documents(m)[doc.id]
    resolved = resolve_sheet_format(m, record, (K.COVER, K.SCHEMATIC))
    assert (resolved.width_mm, resolved.height_mm) == (420, 297)


def test_house_sheet_when_schematic_is_requested_but_the_location_has_no_drawing_set():
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        notes=None,
        remove=(K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    m = model(c1, doc)
    record = documents(m)[doc.id]
    resolved = resolve_sheet_format(m, record, (K.COVER, K.SCHEMATIC))
    assert (resolved.width_mm, resolved.height_mm) == (420, 297)


def test_project_facts_are_empty_with_no_project_record():
    c1 = location("C1", "Demo cabinet")
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=c1, cover="# Cover")
    m = model(c1, doc)
    assert project_facts(m) == ("", "", "", "", "", "")


def test_document_facts_for_a_location_document_matches_project_facts():
    """No units in the model: `document_facts` is byte-identical to `project_facts` (the
    pdf package's own golden(s) must not move for a model with no units)."""
    c1 = location("C1", "Demo cabinet")
    p = project()
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=c1, cover="# Cover")
    m = model(c1, p, doc)
    record = documents(m)[doc.id]
    assert document_facts(m, record) == project_facts(m)


def test_document_facts_for_a_unit_document_uses_the_units_own_current_revision_and_date():
    """Units spec U3, amended by UNIT-ID I2: title/number are the unit's own (empty here, the
    fixture sets none), customer is empty, author stays `Project`'s; revision and revision
    date come from the unit's release's own history entry whose `revision` matches
    `UnitRelease.revision` -- not merely its latest entry (`UnitRelease.revision=1` here,
    with a later revision 2 entry present and a distinct date, so a "last entry" bug would read
    the wrong one), and not `Project`'s own revision date (set different on purpose, so a
    "reads Project's date" bug would too)."""
    c1 = location("C1", "Demo cabinet")
    p = project(revision=9)
    rp = revision_entry("rp", unit=None, revision=9, date="2020-01-01")
    u = unit("u1", name="pump-cabinet", revision=1)
    r1 = revision_entry("r1", unit=u, revision=1, date="2026-09-01", text="First release")
    r2 = revision_entry("r2", unit=u, revision=2, date="2026-09-23", text="Later")
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=u, cover="# Cover")
    m = model(c1, p, rp, u, r1, r2, doc)
    record = documents(m)[doc.id]
    title, number, customer, revision, revision_date, author = document_facts(m, record)
    assert (title, number, customer, author) == ("", "", "", p.author)
    assert (revision, revision_date) == ("1.1", "2026-09-01")


def test_document_facts_revision_date_is_empty_with_no_matching_revision_entry():
    u = unit("u1", name="pump-cabinet", revision=3)
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=u, cover="# Cover")
    m = model(u, doc)
    record = documents(m)[doc.id]
    _title, _number, _customer, revision, revision_date, _author = document_facts(m, record)
    assert (revision, revision_date) == ("1.3", "")


def test_subject_label_for_a_unit_document_is_the_units_name_when_it_has_no_title():
    u = unit("u1", name="pump-cabinet", revision=2)
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=u, cover="# Cover")
    m = model(u, doc)
    record = documents(m)[doc.id]
    assert subject_label(m, record) == "pump-cabinet"


def test_subject_label_for_a_unit_document_is_the_units_title_when_it_has_one():
    """Decision model-0066: the title, not the code name, when both differ."""
    u = unit("u1", name="pump-cabinet", revision=2, title="Pump cabinet")
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=u, cover="# Cover")
    m = model(u, doc)
    record = documents(m)[doc.id]
    assert subject_label(m, record) == "Pump cabinet"


def test_the_cover_heading_of_a_unit_document_carries_the_units_title():
    u = unit("u1", name="relay-interface-board", title="Relay interface board")
    doc = document("d1", preset=DocumentPreset.PCB_SCHEMATIC, subject=u, cover="# Cover")
    m = model(u, doc)
    record = documents(m)[doc.id]
    assert document_heading(m, record) == "PCB schematic \N{EM DASH} Relay interface board"
    assert "Relay interface board" in cover_page(m, record)
    assert "relay-interface-board" not in cover_page(m, record)


def test_the_cover_heading_of_a_unit_document_carries_the_name_when_the_title_is_empty():
    u = unit("u1", name="relay-interface-board")
    doc = document("d1", preset=DocumentPreset.PCB_SCHEMATIC, subject=u, cover="# Cover")
    m = model(u, doc)
    record = documents(m)[doc.id]
    assert document_heading(m, record) == "PCB schematic \N{EM DASH} relay-interface-board"


def test_the_scope_cell_of_a_unit_document_page_prints_the_title_not_the_name():
    """The Scope cell of a schematic page of a unit document, end to end through `source()`."""
    c1 = location("C1", "First cabinet")
    u = unit("u1", name="relay-interface-board", title="Relay interface board")
    ds = drawing_set("ds1", location=c1, unit=u, number=1)
    page = layout_page("p1", drawing_set=ds, number=1)
    doc = document(
        "d1",
        preset=DocumentPreset.PCB_SCHEMATIC,
        subject=u,
        cover="# Cover",
        notes=None,
        remove=(K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    m = model(c1, u, ds, page, doc)
    text = source(m, doc.id, {render_id(page.id): "<svg>one</svg>"})
    assert '"Relay interface board"' in text  # the scope cell
    assert "relay-interface-board" not in text


def test_subject_label_and_heading_for_the_system_preset_have_no_dangling_subject():
    doc = document("d1", preset=DocumentPreset.SYSTEM, cover="# Cover")
    m = model(doc)
    record = documents(m)[doc.id]
    assert subject_label(m, record) == ""
    assert document_heading(m, record) == "System"


def test_source_does_not_crash_with_no_project_record():
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=c1,
        cover="# Cover",
        notes=None,
        remove=(K.CONTENTS, K.HARNESS_DRAWING, K.BOM),
    )
    m = model(c1, doc)
    text = source(m, doc.id, {})
    assert 'text("")' in text  # the empty title, in the header


def test_subject_label_for_an_item_with_a_part_and_no_authored_text_uses_the_parts_description():
    demo_part = part("relay", description="Invented relay")
    board = item("a1", description="", part=demo_part.id)
    doc = document(
        "d1", preset=DocumentPreset.PCB_SCHEMATIC, subject=board, cover="# Cover", notes=None
    )
    m = model(demo_part, board, doc)
    record = documents(m)[doc.id]
    assert document_heading(m, record) == "PCB schematic — A1 Invented relay"


def test_subject_label_for_an_item_with_a_part_and_authored_text_shows_the_authored_text():
    """The heading asks `derive.item_description`: an authored text wins over the part's."""
    demo_part = part("relay", description="Invented relay")
    board = item("a1", description="Authored relay text", part=demo_part.id)
    doc = document(
        "d1", preset=DocumentPreset.PCB_SCHEMATIC, subject=board, cover="# Cover", notes=None
    )
    m = model(demo_part, board, doc)
    record = documents(m)[doc.id]
    heading = document_heading(m, record)
    assert heading == "PCB schematic — A1 Authored relay text"
    assert "Invented relay" not in heading


def test_subject_label_for_an_item_without_a_part_falls_back_to_its_own_description():
    board = item("a1", description="Invented board, no part yet")
    doc = document(
        "d1", preset=DocumentPreset.PCB_SCHEMATIC, subject=board, cover="# Cover", notes=None
    )
    m = model(board, doc)
    record = documents(m)[doc.id]
    assert document_heading(m, record) == "PCB schematic — A1 Invented board, no part yet"


def _harness_with_two_cables(*, remove=(K.BOM,)):
    """A harness with two cables, `W1` and `W2`, each with its own part and product facts
    (RW4b, decision model-0108: a cable is `is_cable`'s own, so both need a cable part)."""
    harness = item("wh1", description="Demo harness")
    demo_part = part("cab1", description="Invented 4-core cable")
    cable1 = item("w1", description="Cable one", part=demo_part.id, parent=harness.id)
    cf1 = cable_facet("w1", subject=cable1.id, length_mm=1500)
    cpf1 = cable_product_facet("w1", subject=demo_part.id)
    demo_part2 = part("cab2", description="Cable two part")
    cable2 = item("w2", description="Cable two", part=demo_part2.id, parent=harness.id)
    cf2 = cable_facet("w2", subject=cable2.id, length_mm=None)
    cpf2 = cable_product_facet("w2", subject=demo_part2.id, core_count=0)
    doc = document(
        "d1",
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=harness,
        cover="# Cover",
        notes=None,
        remove=remove,
    )
    m = model(harness, demo_part, cable1, cf1, cpf1, demo_part2, cable2, cf2, cpf2, doc)
    return m, doc, cable1, cable2


def test_contents_table_renders_every_column_for_a_two_cable_harness():
    m, doc, _cable1, _cable2 = _harness_with_two_cables(remove=(K.HARNESS_DRAWING, K.BOM))
    text = source(m, doc.id, {})
    for header in ("Designation", "MPN", "Description", "Cores", "Gauge", "Length mm", "Ends"):
        assert f'"{header}"' in text
    assert '"-WH1-W1"' in text  # harness-prefixed (H1, decision model-0043)
    assert '"SIM-CAB1"' in text  # the cable's part MPN
    assert '"Invented 4-core cable"' in text
    assert '"4"' in text  # core_count
    assert '"0.5"' in text  # gauge_mm2
    assert '"1500"' in text  # length_mm
    assert '"-WH1-W2"' in text  # the second cable, harness-prefixed too


def test_contents_table_ends_column_reads_the_lower_ranked_end_first():
    """A `W11`-shaped cable, motor `M1` to cabinet strip `X3`, both located: the CONTENTS page's
    "Ends" column reads `X3` before `M1` (decision model-0048, `designation.cable_end_rank`), the
    cabinet's location `"aa-cabinet"` sorting before the motor's `"zz-motor"`.

    The location keys are chosen so location order *disagrees* with alphabetical designation
    order (`"M1" < "X3"` but `"aa-cabinet" < "zz-motor"` puts the cabinet first): a query still
    reading the old `(designation, item)` order would print `"M1 - X3"` instead, so this is a
    real test of `cable_end_rank`, not of alphabetising two designations that already agree with
    it. The core is also authored strip-port-first, on purpose: only a real reorientation, not
    authoring order or port-id luck, can make the rendered text read cabinet-first.
    """
    harness = item("wh1", description="Demo harness")
    m1_item, _m1_fn, m1_port = pin("m1", "M1")
    x3_item, _x3_fn, x3_port = pin("x3", "X3")
    cabinet_loc = location("aa-cabinet", "Cabinet")
    motor_loc = location("zz-motor", "Motor room")
    m1_place = place("m1-loc", item=m1_item.id, node=motor_loc.id)
    x3_place = place("x3-loc", item=x3_item.id, node=cabinet_loc.id)
    cable_part = part("cab11", description="Invented 1-core cable")
    cable = item("w11", description="Cable eleven", part=cable_part.id, parent=harness.id)
    cf = cable_facet("w11", subject=cable.id, length_mm=None)
    cpf = cable_product_facet("w11", subject=cable_part.id, core_count=1)
    core = conductor(
        "core-1", a=x3_port.id, b=m1_port.id, kind=ConductorKind.CORE, carrier=cable.id
    )
    cf1 = core_facet("core-1", subject=core.id, index=1)
    doc = document(
        "d1",
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=harness,
        cover="# Cover",
        notes=None,
        remove=(K.HARNESS_DRAWING, K.BOM),
    )
    m = model(
        harness,
        m1_item,
        _m1_fn,
        m1_port,
        x3_item,
        _x3_fn,
        x3_port,
        motor_loc,
        cabinet_loc,
        m1_place,
        x3_place,
        cable_part,
        cable,
        cf,
        cpf,
        core,
        cf1,
        doc,
    )
    text = source(m, doc.id, {})
    assert '"+aa-cabinet-X3 \N{EN DASH} +zz-motor-M1"' in text
    assert '"+zz-motor-M1 \N{EN DASH} +aa-cabinet-X3"' not in text


def test_contents_page_is_left_out_for_a_harness_with_no_cable():
    harness = item("wh1", description="Demo harness")
    doc = document(
        "d1",
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=harness,
        cover="# Cover",
        notes=None,
        remove=(K.HARNESS_DRAWING, K.BOM),
    )
    m = model(harness, doc)
    text = source(m, doc.id, {})
    assert "None." not in text
    assert '#heading(level: 1, text("Cover"))' in text  # the cover is still there
    assert text.count("#pagebreak()") == 0  # the cover alone: the empty list has no page (pdf-0019)


def test_contents_page_is_left_out_when_added_to_a_location_subject_document():
    """`add=(K.CONTENTS,)` is a legitimate authoring choice on a location subject too (decision
    0023 puts no restriction on which subject a page kind may be added to); `record.item is
    None` there, so the page is left out, never a crash or a leaked table."""
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        notes=None,
        add=(K.CONTENTS,),
        remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    m = model(c1, doc)
    text = source(m, doc.id, {})
    assert "None." not in text
    assert '#heading(level: 1, text("Cover"))' in text  # the cover is still there
    assert text.count("#pagebreak()") == 0  # the cover alone: the empty list has no page (pdf-0019)
    assert text.count("#table") == 0  # no cable table; the cover carries no table either (R10)


def test_harness_drawing_renders_one_block_per_harness():
    """A harness of two cables is one block (CD9), keyed by the harness, in the "No part number"
    run since the harness has no part of its own: not one page per cable, not the cables' parts."""
    m, doc, cable1, _cable2 = _harness_with_two_cables(remove=(K.CONTENTS, K.BOM))
    text = source(m, doc.id, {cable_block_key(None, cable1.parent): "<svg>harness-block</svg>"})
    assert text.count("<svg>harness-block</svg>") == 1
    assert "#align(center)" not in text  # P8's caption is gone (page-frame R3, R4)
    assert '"No part number"' in text
    assert '"SIM-CAB1"' not in text
    assert '"SIM-CAB2"' not in text


def test_harness_drawing_never_falls_back_to_no_drawings_once_a_cable_is_found():
    """A found cable's block page is built from its svgs entry, never `No drawings.`: the block
    is the page's one image."""
    m, doc, cable1, _cable2 = _harness_with_two_cables(remove=(K.CONTENTS, K.BOM))
    text = source(m, doc.id, {cable_block_key(None, cable1.parent): "<svg>harness-block</svg>"})
    assert '#par(text("No drawings."))' not in text
    assert "<svg>harness-block</svg>" in text


def test_harness_cables_for_is_empty_for_a_location_subject():
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=c1, cover="# Cover", notes=None
    )
    m = model(c1, doc)
    record = documents(m)[doc.id]
    assert harness_cables_for(m, record, (K.HARNESS_DRAWING,)) == ()


def test_harness_cables_for_is_empty_when_neither_harness_page_kind_is_requested():
    m, doc, _cable1, _cable2 = _harness_with_two_cables(remove=(K.CONTENTS, K.HARNESS_DRAWING))
    record = documents(m)[doc.id]
    assert harness_cables_for(m, record, (K.COVER,)) == ()


_SYSTEM_CABLE_PAGE_COUNT = 2


def test_system_preset_renders_a_harness_drawing_page_per_top_level_cable():
    """Units spec U3: the `system` document's cable drawings are every top-level cable
    (`derive.top_level_cables`), not a single harness subject -- it has none of the three.
    Exercises the whole `system` preset end to end: its default pages (`presets.py`) resolve,
    render and check without crashing, with a sensible, non-crashing scope label."""
    demo_part = part("cab1", description="Invented 4-core cable")
    cable1 = item("w1", description="Cable one", part=demo_part.id)
    cf1 = cable_facet("w1", subject=cable1.id, length_mm=1500)
    cpf1 = cable_product_facet("w1", subject=demo_part.id)
    demo_part2 = part("cab2", description="Cable two part")
    cable2 = item("w2", description="Cable two", part=demo_part2.id)
    cf2 = cable_facet("w2", subject=cable2.id, length_mm=None)
    cpf2 = cable_product_facet("w2", subject=demo_part2.id, core_count=0)
    doc = document("d1", preset=DocumentPreset.SYSTEM, cover="# Cover", notes=None)
    m = model(demo_part, cable1, cf1, cpf1, demo_part2, cable2, cf2, cpf2, doc)
    svgs = {
        cable_block_key(None, cable.id): f"<svg>{cable.id.value}</svg>"
        for cable in (cable1, cable2)
    }
    text = source(m, doc.id, svgs)
    assert text.count('format: "svg")') == _SYSTEM_CABLE_PAGE_COUNT
    assert all(svg in text for svg in svgs.values())
    assert '"System"' in text  # the heading, no dangling "-- subject"


def test_system_preset_with_no_top_level_cable_contributes_no_harness_drawing_page():
    """STEP 4b addition (decision pdf-0006, units spec U3's amended "cable drawings" bullet):
    a `system` document over a model with no top-level cable at all gives its HARNESS_DRAWING
    section no page at all -- not even the NO_DRAWINGS text page a harness-with-no-cable
    document still gets (`test_harness_drawing_falls_back_to_no_drawings_for_a_cableless_
    harness` below, unchanged). `checks.py`'s `DOCUMENT_NO_TOP_LEVEL_CABLES` covers the
    finding side (`test_checks.py`).
    """
    doc = document("d1", preset=DocumentPreset.SYSTEM, cover="# Cover", notes=None)
    m = model(doc)
    text = source(m, doc.id, {})
    assert '#par(text("No drawings."))' not in text
    assert 'text(size: 10pt, text("Harness drawing"))' not in text


def test_system_preset_with_one_top_level_cable_draws_its_page_and_no_no_drawings():
    """The clean twin, can-fail 1's own positive proof: one top-level cable in the model gives
    the HARNESS_DRAWING section its one real page, not the empty-section case above."""
    cable_part = part("w1", description="Cable one part")
    cable_product = cable_product_facet("w1", subject=cable_part.id, core_count=0)
    cable = item("w1", description="Cable one", part=cable_part.id)
    cf = cable_facet("w1", subject=cable.id, length_mm=None)
    doc = document("d1", preset=DocumentPreset.SYSTEM, cover="# Cover", notes=None)
    m = model(cable, cf, cable_part, cable_product, doc)
    text = source(m, doc.id, {cable_block_key(None, cable.id): "<svg>lone-cable</svg>"})
    assert text.count("<svg>lone-cable</svg>") == 1
    assert '#par(text("No drawings."))' not in text


def test_system_preset_with_contents_lists_its_top_level_cables_not_none():
    """`CONTENTS` added to the `SYSTEM` preset (no item, no unit) lists every top-level cable, the
    ones its HARNESS_DRAWING draws (`harness_cables_for`), where it used to print `None.`."""
    cable_part = part("cab1", description="Invented 1-core cable")
    cable1 = item("w1", description="Cable one", part=cable_part.id)
    cf1 = cable_facet("w1", subject=cable1.id, length_mm=1500)
    cpf = cable_product_facet("w1", subject=cable_part.id, core_count=1)
    cable_part2 = part("cab2", description="Cable two part")
    cable2 = item("w2", description="Cable two", part=cable_part2.id)
    cf2 = cable_facet("w2", subject=cable2.id, length_mm=None)
    cpf2 = cable_product_facet("w2", subject=cable_part2.id, core_count=0)
    m1_item, m1_fn, m1_port = pin("m1", "M1")
    x3_item, x3_fn, x3_port = pin("x3", "X3")
    core = conductor(
        "core-1", a=m1_port.id, b=x3_port.id, kind=ConductorKind.CORE, carrier=cable1.id
    )
    core_marker = core_facet("core-1", subject=core.id, index=1)
    doc = document(
        "d1",
        preset=DocumentPreset.SYSTEM,
        cover="# Cover",
        notes=None,
        add=(K.CONTENTS,),
        remove=(K.HARNESS_DRAWING, K.CABLE_LIST, K.BOM),  # the other pages may print `None.` too
    )
    m = model(
        cable_part,
        cable1,
        cf1,
        cpf,
        cable_part2,
        cable2,
        cf2,
        cpf2,
        m1_item,
        m1_fn,
        m1_port,
        x3_item,
        x3_fn,
        x3_port,
        core,
        core_marker,
        doc,
    )
    found = harness_cables_for(m, documents(m)[doc.id], (K.CONTENTS,))
    assert {cable.cable for cable in found} == {cable1.id, cable2.id}
    text = source(m, doc.id, {})
    # Written out from the fixture's tags `W1`, `W2`, `M1`, `X3`, none placed: `-` plus the tag.
    assert 'text("-W1")' in text
    assert 'text("-W2")' in text
    assert 'text("-M1 \N{EN DASH} -X3")' in text
    assert "#table(columns: 7" in text
    assert '#par(text("None."))' not in text


def test_harness_drawing_falls_back_to_no_drawings_for_a_cableless_harness():
    harness = item("wh1", description="Demo harness")
    doc = document(
        "d1",
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=harness,
        cover="# Cover",
        notes=None,
        remove=(K.CONTENTS, K.BOM),
    )
    m = model(harness, doc)
    text = source(m, doc.id, {})
    assert '#par(text("No drawings."))' in text


def test_schematic_no_drawings_page_sets_its_own_title_block_after_a_notes_page():
    """The confirmed bug (page-frame R3, R4): `schematic_source`'s NO_DRAWINGS early return
    used to be a bare paragraph with no `#set page`/`#page` of its own, so in Typst's
    page-flow model it silently inherited whichever `#set page(background: ...)` was last in
    effect -- here, the preceding NOTES page's own title "Notes", not its own. A cabinet
    document with a NOTES page and no drawing set reproduces that shape directly.
    """
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        notes="Some notes.",
        remove=(K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    m = model(c1, doc)
    text = source(m, doc.id, {})
    assert text.count('#par(text("No drawings."))') == 1
    assert "#page(margin: " in text  # the body is wrapped in its own page, not bare
    # Proves the page carries its OWN title cell, not the NOTES page's: pre-fix, this cell
    # pair never appears anywhere in the source (the bare paragraph sets no title block).
    assert 'text(size: 8pt, "Page title"), text(size: 10pt, text("Schematic"))' in text


def test_harness_drawing_no_drawings_page_sets_its_own_title_block_after_a_notes_page():
    """Same bug, `harness_drawing_source`'s own NO_DRAWINGS path. Moved from the `system`
    document with no cable this test originally used (decision pdf-0006, STEP 4b addition):
    that case no longer falls back to NO_DRAWINGS at all (`DOCUMENT_NO_TOP_LEVEL_CABLES`
    INFO, no page -- `test_harness_drawing_no_cable_source_variants` below), so the
    NO_DRAWINGS-after-NOTES regression shape now needs a genuine harness document naming a
    harness with no cable instead, which still falls back to NO_DRAWINGS unchanged.
    """
    harness = item("wh1", description="Demo harness")
    doc = document(
        "d1",
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=harness,
        cover="# Cover",
        notes="Some notes.",
        remove=(K.CONTENTS, K.BOM),
    )
    m = model(harness, doc)
    text = source(m, doc.id, {})
    assert text.count('#par(text("No drawings."))') == 1
    assert "#page(margin: " in text  # the body is wrapped in its own page, not bare
    assert 'text(size: 8pt, "Page title"), text(size: 10pt, text("Harness drawing"))' in text
