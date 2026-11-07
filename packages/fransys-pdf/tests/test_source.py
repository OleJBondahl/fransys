"""`source`: page geometry, cover and notes."""

import dataclasses

import fransys_render
import pytest
from _build import (
    FLOW,
    PDF,
    REVISION_HEADERS,
    WORDS,
    cable_facet,
    cable_product_facet,
    conductor,
    connector,
    document,
    drawing_set,
    item,
    layout_page,
    location,
    model,
    part,
    pcb_facet,
    pin,
    place,
    plc_channel,
    project,
    revision_entry,
    sheet_format,
    source,
    terminal,
    unit,
    wire_facet,
)
from fransys_pdf import _lists
from fransys_pdf._drawings import schematic_pages
from fransys_pdf._geometry import document_heading
from fransys_pdf._pages import cover_page as _cover_page

from electrical_symbols import LIBRARY
from fransys_model.derive import (
    SheetKey,
    document_facts,
    document_row,
    document_rows,
    document_sheets_of,
    harness_cables_for,
    project_facts,
    subject_label,
)
from fransys_model.derive import document_sheet_format as resolve_sheet_format
from fransys_model.derive.cable_drawing import cable_block_key
from fransys_model.derive.harness_blocks import _part_line
from fransys_model.kernel import make_id, render_id
from fransys_model.vocab import (
    DocumentPreset,
    Net,
    NetClass,
    PageKind,
    SignalType,
)

K = PageKind
_PRESET = DocumentPreset.CABINET_SCHEMATIC

# Unit documents: named non-zero counts for the two-drawing-set fixtures below.
_UNIT_DOCUMENT_PAGE_COUNT = 2


def _cabinet(**overrides):
    c1 = location("C1", "Demo cabinet")
    p = project()
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cabinet cover\n\nSome cover text.",
        notes=overrides.pop("notes", "Some notes."),
    )
    return model(c1, p, doc), doc


def test_cover_and_notes_pages_are_separated_by_a_page_break():
    m, doc = _cabinet()
    text = source(m, doc.id, {}, fransys_render.sheets(document_sheets_of(m, ()), LIBRARY), diagrams=())
    assert text.count("#pagebreak()") == 2  # COVER|NOTES, then NOTES|SCHEMATIC (the preset's own no-drawings page)


def _cover(m, doc):
    return _cover_page(m, doc, REVISION_HEADERS, 120.0)


def test_cover_has_no_facts_table_but_keeps_its_own_heading_and_text():
    """The cover drops the six `Project` facts as a table; the
    title block already carries them on every page, the cover included. Paired
    absence/presence on `cover_page` alone, not the whole `source()`, so a blank cover cannot
    pass this check by accident -- the whole document still contains the facts through the
    title block in the page background."""
    m, doc = _cabinet()
    text = _cover(m, doc)
    assert "#table" not in text  # absence: no fact table of any shape
    assert '"DEMO-1"' not in text  # absence: Project.number, only in the title block now
    assert '"Demo Co"' not in text  # absence: Project.customer, likewise
    assert '#heading(level: 1, text("Cabinet cover"))' in text  # presence: the cover's own heading
    assert '"Some cover text."' in text  # presence: the cover's own text
    assert "Cabinet schematic" in text  # presence: preset words, part of the document heading
    assert "C1 Demo cabinet" in text  # presence: subject label, part of the document heading


def test_cover_markdown_is_rendered():
    m, doc = _cabinet()
    text = source(m, doc.id, {}, fransys_render.sheets(document_sheets_of(m, ()), LIBRARY), diagrams=())
    assert '#heading(level: 1, text("Cabinet cover"))' in text
    assert '"Some cover text."' in text


def test_no_notes_page_when_there_is_no_notes_text():
    m, doc = _cabinet(notes=None)
    text = source(m, doc.id, {}, fransys_render.sheets(document_sheets_of(m, ()), LIBRARY), diagrams=())
    assert '"Notes"' not in text
    assert text.count("#pagebreak()") == 1  # COVER|SCHEMATIC only: no NOTES page, so no break around it


def test_house_sheet_when_the_document_has_no_drawing_pages():
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        notes=None,
    )
    m = model(c1, doc)
    sheet = resolve_sheet_format(m, doc.id, (K.COVER,))
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
    )
    m = model(c1, ds, p2, p1, doc)  # inserted out of number order: proves the sort, not insertion
    svgs = {
        render_id(p1.id): "<svg>one</svg>",
        render_id(p2.id): "<svg>two</svg>",
    }
    text = source(m, doc.id, svgs, fransys_render.sheets(document_sheets_of(m, ()), LIBRARY), diagrams=())
    assert text.count("#page(margin: 0mm, background:") == 2  # full bleed
    assert text.index("<svg>one</svg>") < text.index("<svg>two</svg>")
    assert text.count("#pagebreak()") == 3  # COVER|SHEET_INDEX, SHEET_INDEX|SCHEMATIC, then between the two SCHEMATIC pages


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
    )
    m = model(c1, ds, p1, p2, doc)
    svgs = {render_id(p1.id): "<svg>one</svg>"}
    text = source(m, doc.id, svgs, fransys_render.sheets(document_sheets_of(m, ()), LIBRARY), diagrams=())
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
    )
    m = model(c1, doc)
    text = source(m, doc.id, {}, fransys_render.sheets(document_sheets_of(m, ()), LIBRARY), diagrams=())
    assert '#par(text("No drawings."))' in text


def test_schematic_pages_fall_back_to_no_drawings_for_an_item_subject():
    board = item("a1", description="Invented board")
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=board,
        cover="# Cover",
        notes=None,
    )
    m = model(board, doc)
    text = source(m, doc.id, {}, fransys_render.sheets(document_sheets_of(m, ()), LIBRARY), diagrams=())
    assert '#par(text("No drawings."))' in text


def test_location_document_picks_only_the_unit_none_set_at_its_location():
    """The join-key fix (model-0041 amending decision 0024): a location subject
    matches `unit is None` at that location, never a nested unit's own set that happens to
    share the location node. `ds_nested`'s `number` (1) sorts before `ds_top`'s (2) on
    purpose: the old `min(..., key=number)` body, filtering by location alone, would have
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
    )
    m = model(c1, u, ds_nested, ds_top, p_nested, p_top, doc)
    record = document_row(m, doc.id)
    pages = schematic_pages(m, record, (K.SCHEMATIC,))
    assert list(pages) == [p_top.id]


def test_unit_document_gets_pages_from_every_one_of_its_units_sets_in_location_order():
    """A unit document's schematic pages span every drawing set of its unit, any location,
    sorted by the sets' own `number` (layout-0045: unit-then-location order), then page
    number within each set ("in location order" for `cabinet_schematic` with
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
    )
    m = model(c1, c2, u, ds1, ds2, p1, p2, doc)
    record = document_row(m, doc.id)
    pages = schematic_pages(m, record, (K.SCHEMATIC,))
    assert len(pages) == _UNIT_DOCUMENT_PAGE_COUNT
    assert list(pages) == [p1.id, p2.id]


def test_unit_document_source_wires_title_block_scope():
    """Integration proof, end to end through `source()`'s own `schematic_source` section, not
    the lower-level functions alone: `document_facts`' unit revision/date, the
    unit-name scope cell (`subject_label`).
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
    )
    m = model(c1, c2, u, r1, r2, p, rp, ds1, ds2, page1, page2, doc)
    svgs = {render_id(page1.id): "<svg>one</svg>", render_id(page2.id): "<svg>two</svg>"}
    sheets = fransys_render.sheets(document_sheets_of(m, ()), LIBRARY)
    text = source(m, doc.id, svgs, sheets, diagrams=())
    first, second = (sheets[SheetKey(doc.id, K.SCHEMATIC, i)].svg for i in (0, 1))
    assert ">2026-09-01</text>" in first  # the unit's own current revision date
    assert "2020-01-01" not in first + second + text  # never Project's
    assert ">pump-cabinet</text>" in first  # the scope cell


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
    )
    m = model(c1, fmt, ds, page, doc)
    record = document_row(m, doc.id)
    resolved = resolve_sheet_format(m, record.id, (K.COVER, K.SCHEMATIC))
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
    )
    m = model(c1, ds, page, doc)
    record = document_row(m, doc.id)
    resolved = resolve_sheet_format(m, record.id, (K.COVER, K.SCHEMATIC))
    assert (resolved.width_mm, resolved.height_mm) == (420, 297)


def test_house_sheet_when_schematic_is_requested_but_the_location_has_no_drawing_set():
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        notes=None,
    )
    m = model(c1, doc)
    record = document_row(m, doc.id)
    resolved = resolve_sheet_format(m, record.id, (K.COVER, K.SCHEMATIC))
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
    record = document_row(m, doc.id)
    assert document_facts(m, record.id) == project_facts(m)


def test_document_facts_for_a_unit_document_uses_the_units_own_current_revision_and_date():
    """Title/number are the unit's own (empty here, the
    fixture sets none), customer is empty, author is the unit revision's `created` (pdf-0036 D5, not
    `Project`'s); revision and revision
    date come from the unit's release's own history entry whose `revision` matches
    """
    c1 = location("C1", "Demo cabinet")
    p = project(revision=9)
    rp = revision_entry("rp", unit=None, revision=9, date="2020-01-01")
    u = unit("u1", name="pump-cabinet", revision=1)
    r1 = revision_entry("r1", unit=u, revision=1, date="2026-09-01", text="First release", created="AB")
    r2 = revision_entry("r2", unit=u, revision=2, date="2026-09-23", text="Later", created="CD")
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=u, cover="# Cover")
    m = model(c1, p, rp, u, r1, r2, doc)
    record = document_row(m, doc.id)
    title, number, customer, revision, revision_date, author = document_facts(m, record.id)
    assert (title, number, customer, author) == ("", "", "", "AB")
    assert p.author != "AB"
    assert (revision, revision_date) == ("1.1", "2026-09-01")


def test_document_facts_revision_date_is_empty_with_no_matching_revision_entry():
    u = unit("u1", name="pump-cabinet", revision=3)
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=u, cover="# Cover")
    m = model(u, doc)
    record = document_row(m, doc.id)
    _title, _number, _customer, revision, revision_date, _author = document_facts(m, record.id)
    assert (revision, revision_date) == ("1.3", "")


def test_subject_label_for_a_unit_document_is_the_units_name_when_it_has_no_title():
    u = unit("u1", name="pump-cabinet", revision=2)
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=u, cover="# Cover")
    m = model(u, doc)
    record = document_row(m, doc.id)
    assert subject_label(m, record.id) == "pump-cabinet"


def test_subject_label_for_a_unit_document_is_the_units_title_when_it_has_one():
    """Decision model-0066: the title, not the code name, when both differ."""
    u = unit("u1", name="pump-cabinet", revision=2, title="Pump cabinet")
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=u, cover="# Cover")
    m = model(u, doc)
    record = document_row(m, doc.id)
    assert subject_label(m, record.id) == "Pump cabinet"


def test_the_cover_heading_of_a_unit_document_carries_the_units_title():
    u = unit("u1", name="relay-interface-board", title="Relay interface board")
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=u, cover="# Cover")
    m = model(u, doc)
    record = document_row(m, doc.id)
    assert document_heading(m, record) == "Cabinet schematic \N{EM DASH} Relay interface board"
    assert "Relay interface board" in _cover(m, record)
    assert "relay-interface-board" not in _cover(m, record)


def test_the_cover_heading_of_a_unit_document_carries_the_name_when_the_title_is_empty():
    u = unit("u1", name="relay-interface-board")
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=u, cover="# Cover")
    m = model(u, doc)
    record = document_row(m, doc.id)
    assert document_heading(m, record) == "Cabinet schematic \N{EM DASH} relay-interface-board"


def test_the_scope_cell_of_a_unit_document_page_prints_the_title_not_the_name():
    """The Scope cell of a schematic page of a unit document, end to end through `source()`."""
    c1 = location("C1", "First cabinet")
    u = unit("u1", name="relay-interface-board", title="Relay interface board")
    ds = drawing_set("ds1", location=c1, unit=u, number=1)
    page = layout_page("p1", drawing_set=ds, number=1)
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=u,
        cover="# Cover",
        notes=None,
    )
    m = model(c1, u, ds, page, doc)
    text = source(
        m,
        doc.id,
        {render_id(page.id): "<svg>one</svg>"},
        fransys_render.sheets(document_sheets_of(m, ()), LIBRARY),
        diagrams=(),
    )
    assert '"Relay interface board"' in text  # the scope cell
    assert "relay-interface-board" not in text


def test_subject_label_and_heading_for_the_system_preset_have_no_dangling_subject():
    doc = document("d1", preset=DocumentPreset.SYSTEM, cover="# Cover")
    m = model(doc)
    record = document_row(m, doc.id)
    assert subject_label(m, record.id) == ""
    assert document_heading(m, record) == "System"


def test_source_does_not_crash_with_no_project_record():
    c1 = location("C1", "Demo cabinet")
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=c1, cover="# Cover", notes=None)
    m = model(c1, doc)
    sheets = fransys_render.sheets(document_sheets_of(m, ()), LIBRARY)
    text = source(m, doc.id, {}, sheets, diagrams=())
    assert '#set document(title: ""' in text  # the empty title, in the metadata
    assert ">Title</text>" in sheets[SheetKey(doc.id, K.COVER, 0)].svg  # the cell still prints


def test_subject_label_for_an_item_with_a_part_and_no_authored_text_uses_the_parts_description():
    demo_part = part("relay", description="Invented relay")
    board = item("a1", description="", part=demo_part.id)
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=board, cover="# Cover", notes=None)
    m = model(demo_part, board, doc)
    record = document_row(m, doc.id)
    assert document_heading(m, record) == "Cabinet schematic — A1 Invented relay"


def test_subject_label_for_an_item_with_a_part_and_authored_text_shows_the_authored_text():
    """The heading asks `derive.item_description`: an authored text wins over the part's."""
    demo_part = part("relay", description="Invented relay")
    board = item("a1", description="Authored relay text", part=demo_part.id)
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=board, cover="# Cover", notes=None)
    m = model(demo_part, board, doc)
    record = document_row(m, doc.id)
    heading = document_heading(m, record)
    assert heading == "Cabinet schematic — A1 Authored relay text"
    assert "Invented relay" not in heading


def test_subject_label_for_an_item_without_a_part_falls_back_to_its_own_description():
    board = item("a1", description="Invented board, no part yet")
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=board, cover="# Cover", notes=None)
    m = model(board, doc)
    record = document_row(m, doc.id)
    assert document_heading(m, record) == "Cabinet schematic — A1 Invented board, no part yet"


def test_harness_cables_for_is_empty_for_a_location_subject():
    c1 = location("C1", "Demo cabinet")
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=c1, cover="# Cover", notes=None)
    m = model(c1, doc)
    record = document_row(m, doc.id)
    assert harness_cables_for(m, record.id, (K.HARNESS_DRAWING,)) == ()


def test_harness_cables_for_is_empty_when_neither_harness_page_kind_is_requested():
    cable_part = part("cab1", description="Invented 4-core cable")
    cable = item("w1", description="Cable one", part=cable_part.id)
    cf = cable_facet("w1", subject=cable.id, length_mm=1500)
    cpf = cable_product_facet("w1", subject=cable_part.id)
    doc = document("d1", preset=DocumentPreset.SYSTEM, cover="# Cover", notes=None)
    m = model(cable_part, cable, cf, cpf, doc)
    record = document_row(m, doc.id)
    assert harness_cables_for(m, record.id, (K.COVER,)) == ()


_SYSTEM_CABLE_PAGE_COUNT = 2


def test_system_preset_renders_a_harness_drawing_page_per_top_level_cable():
    """The `system` document's cable drawings are every top-level cable
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
    svgs = {cable_block_key(None, cable.id): f"<svg>{cable.id.value}</svg>" for cable in (cable1, cable2)}
    text = source(m, doc.id, svgs, fransys_render.sheets(document_sheets_of(m, ()), LIBRARY), diagrams=())
    assert text.count("#image(bytes(") == _SYSTEM_CABLE_PAGE_COUNT
    assert all(svg in text for svg in svgs.values())
    assert '"System"' in text  # the heading, no dangling "-- subject"


def test_system_preset_with_no_top_level_cable_contributes_no_harness_drawing_page():
    """The "cable drawings" bullet (decision pdf-0006):
    a `system` document over a model with no top-level cable at all gives its HARNESS_DRAWING
    section no page at all -- not even the NO_DRAWINGS text page a harness-with-no-cable
    document still gets (`test_harness_drawing_falls_back_to_no_drawings_for_a_cableless_
    """
    doc = document("d1", preset=DocumentPreset.SYSTEM, cover="# Cover", notes=None)
    m = model(doc)
    text = source(m, doc.id, {}, fransys_render.sheets(document_sheets_of(m, ()), LIBRARY), diagrams=())
    assert '#par(text("No drawings."))' not in text
    assert not any(key.kind is K.HARNESS_DRAWING for key in fransys_render.sheets(document_sheets_of(m, ()), LIBRARY))  # no page, no cell


def test_system_preset_with_one_top_level_cable_draws_its_page_and_no_no_drawings():
    """The clean twin, can-fail 1's own positive proof: one top-level cable in the model gives
    the HARNESS_DRAWING section its one real page, not the empty-section case above."""
    cable_part = part("w1", description="Cable one part")
    cable_product = cable_product_facet("w1", subject=cable_part.id, core_count=0)
    cable = item("w1", description="Cable one", part=cable_part.id)
    cf = cable_facet("w1", subject=cable.id, length_mm=None)
    doc = document("d1", preset=DocumentPreset.SYSTEM, cover="# Cover", notes=None)
    m = model(cable, cf, cable_part, cable_product, doc)
    text = source(
        m,
        doc.id,
        {cable_block_key(None, cable.id): "<svg>lone-cable</svg>"},
        fransys_render.sheets(document_sheets_of(m, ()), LIBRARY),
        diagrams=(),
    )
    assert text.count("<svg>lone-cable</svg>") == 1
    assert '#par(text("No drawings."))' not in text


def test_schematic_no_drawings_page_sets_its_own_title_block_after_a_notes_page():
    """The confirmed bug: `schematic_source`'s NO_DRAWINGS early return
    used to be a bare paragraph with no `#set page`/`#page` of its own, so in Typst's
    page-flow model it silently inherited whichever `#set page(background: ...)` was last in
    effect -- here, the preceding NOTES page's own title "Notes", not its own. A cabinet
    """
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        notes="Some notes.",
    )
    m = model(c1, doc)
    text = source(m, doc.id, {}, fransys_render.sheets(document_sheets_of(m, ()), LIBRARY), diagrams=())
    assert text.count('#par(text("No drawings."))') == 1
    assert "#page(margin: " in text  # the body is wrapped in its own page, not bare
    # Proves the page carries its OWN title cell, not the NOTES page's: pre-fix, the bare
    # paragraph set no title block, so the page title "Schematic" was nowhere.
    svg = fransys_render.sheets(document_sheets_of(m, ()), LIBRARY)[SheetKey(doc.id, K.SCHEMATIC, None)].svg
    assert ">Schematic</text>" in svg


def _list_pages_model():
    """A cabinet with a strip of one terminal, a PLC module with one channel, a BOM line, a labelled
    wire, a board with one connector and a cable: every list page has a row."""
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=_PRESET,
        subject=c1,
        cover="# Cover",
        notes=None,
    )
    strip = item("x1", description="Strip one")
    t1, t1_facet = terminal("t1", strip=strip.id, group="L", index=1)
    module = item("mod1", description="PLC module")
    module_part, template, fn, facet, channel_pin = plc_channel("ch1", module=module.id, name="ch1", signal=SignalType.DI, channel=1)
    module = dataclasses.replace(module, part=module_part.id)
    a_item, a_fn, a_port = pin("a", "A1")
    b_item, b_fn, b_port = pin("b", "B1")
    wire = conductor("w1", a=a_port.id, b=b_port.id)
    label = wire_facet("w1", subject=wire.id, label="W1")
    board_part = part("board1", description="Invented board")
    board = item("jb1", description="Board one", part=board_part.id)
    conn = connector("j1", item=board.id, name="J1", markings=("1",))
    cable_part = part("cab1", description="Invented 4-core cable")
    cable = item("cb1", description="Cable one", part=cable_part.id)
    cable_records = (cable_part, cable, cable_facet("cb1", subject=cable.id, length_mm=1500))
    cable_records += (cable_product_facet("cb1", subject=cable_part.id),)
    items = (strip, module, a_item, b_item, board)
    placed = [place(f"p-{one.key[-1]}", item=one.id, node=c1.id) for one in items]
    records = (
        c1,
        doc,
        strip,
        t1,
        t1_facet,
        module,
        module_part,
        template,
        fn,
        facet,
        channel_pin,
        *placed,
    )
    records += (a_item, a_fn, a_port, b_item, b_fn, b_port, wire, label, board_part, board)
    records += (pcb_facet("board1", subject=board_part.id), *conn[:4], *conn[4], *cable_records)
    records += (conductor("w-conn", a=conn[4][0].id, b=a_port.id),)  # a wired pin: a table
    records += (document("d2", preset=DocumentPreset.SYSTEM, cover="# Cover", notes=None),)
    return model(*records), doc


def _list_page(page, m, doc, **flow):
    """One flowing list page; the terminal list takes the document's `Doc`."""
    record = document_row(m, doc.id)
    if page == "terminal_list_page":
        return _lists.terminal_list_page(m, record, (WORDS["bridge"], None, 15), **flow)
    return getattr(_lists, page)(m, record, **flow)


_FLOWING = ("terminal_list_page", "plc_list_page", "wire_label_list_page")
_FLOWING += ("designation_list_page", "connector_list_page")


@pytest.mark.parametrize("page", _FLOWING)
def test_a_list_page_declares_two_columns_of_forty_percent(page):
    """A3 (pdf-0026): the source of each flowing list page is one 100 % block of two columns
    with a 20 % gutter, so each column is 40 % of the content width."""
    m, doc = _list_pages_model()
    text = _list_page(page, m, doc, **FLOW)
    assert text.startswith("#block(width: 100%)[#columns(2, gutter: 20%)[")
    assert text.count("#columns(") == 1


@pytest.mark.parametrize("page", _FLOWING)
def test_a_list_page_reads_its_share_and_gutter_from_the_caller(page):
    """A hardcoded share would print 40 % whatever is passed; 41 and 21 must reach the page."""
    m, doc = _list_pages_model()
    text = _list_page(page, m, doc, share_pct=41, gutter_pct=21)
    assert text.startswith("#block(width: 103%)[#columns(2, gutter: 20.3883%)[")


def test_source_passes_the_list_share_down_to_the_list_pages():
    """`source(list_share_pct=41)` changes the list pages against 40: the value is read."""
    m, doc = _list_pages_model()
    sheets = fransys_render.sheets(document_sheets_of(m, ()), LIBRARY)
    wide = source(m, doc.id, {}, sheets, pdf={**PDF, "list_share_pct": 41}, diagrams=())
    assert wide != source(m, doc.id, {}, sheets, diagrams=())
    assert "#block(width: 102%)[" in wide


@pytest.mark.parametrize("page", _FLOWING)
def test_every_flowing_list_page_has_content_inside_its_columns(page):
    """A3 (pdf-0026, B1): the page has rows, so the columns block is not vacuously absent."""
    m, doc = _list_pages_model()
    text = _list_page(page, m, doc, **FLOW)
    assert "#table(" in text


@pytest.mark.parametrize("page", ["cable_list_page", "bom_page"])
def test_the_cable_list_and_the_bom_stay_full_width(page):
    """A3 (pdf-0026, L8; pdf-0027, L14): the cable list and the BOM have a table, no columns.

    The cable list is the system document's: a location document draws no cable (pdf-0042).
    """
    m, _ = _list_pages_model()
    record = next(r for r in document_rows(m) if r.preset is DocumentPreset.SYSTEM)
    text = getattr(_lists, page)(m, record)
    assert "#table(" in text
    assert "#columns(" not in text


def _boards_model(keys, *, on_net):
    """A cabinet with one board per key, each with one connector pin; `on_net` lists it on a net."""
    c1 = location("C1", "Demo cabinet")
    doc = document("d1", preset=_PRESET, subject=c1, cover="# Cover", notes=None)
    records = (c1, doc)
    for key in keys:
        board_part = part(f"{key}-part", description=f"Invented board {key}")
        board = item(key, description=f"Board {key}", part=board_part.id)
        conn = connector(f"j-{key}", item=board.id, name="J1", markings=("1",))
        pcb = pcb_facet(key, subject=board_part.id)
        records += (board_part, board, pcb, place(f"p-{key}", item=board.id, node=c1.id))
        records += (*conn[:4], *conn[4])
        if on_net:
            net_key = ("net", key)
            records += (
                Net(
                    id=make_id(Net, net_key),
                    key=net_key,
                    name=f"N-{key}",
                    net_class=NetClass.SIGNAL,
                    ports=(conn[4][0].id,),
                ),
            )
    m = model(*records)
    return _lists.connector_list_page(m, document_row(m, doc.id), **FLOW)


def test_each_wired_board_of_the_connector_list_keeps_its_heading():
    """B2-1 (pdf-0026): with two boards, each wired board's section keeps its level-2 heading."""
    text = _boards_model(("jb1", "jb2"), on_net=True)

    assert '#heading(level: 2, text("-JB1"))' in text
    assert '#heading(level: 2, text("-JB2"))' in text


def test_cable_page_part_line_counts_conductor_cores_not_the_screen():
    """A cable product of four cores and a screen prints `4 x 0.5 mm²` (pdf-0039)."""
    demo_part = part("cab1", description="Invented screened cable")
    cable = item("w1", description="Cable one", part=demo_part.id)
    product = dataclasses.replace(
        cable_product_facet("w1", subject=demo_part.id),
        core_colours=("BN", "BK", "GY", "BU", "SH"),
    )
    doc = document("d1", preset=DocumentPreset.SYSTEM, cover="# Cover", notes=None)
    m = model(demo_part, cable, cable_facet("w1", subject=cable.id, length_mm=None), product, doc)
    (found,) = harness_cables_for(m, doc.id, (K.HARNESS_DRAWING,))
    assert _part_line(found).endswith("4 x 0.5 mm²")


def test_connector_with_no_wired_pin_prints_one_line_and_no_heading():
    """An unwired connector prints `-JB1: no pin wired` once: no table, no heading (pdf-0039)."""
    text = _boards_model(("jb1",), on_net=False)

    assert text.count("-JB1") == 1
    assert 'text("-JB1: no pin wired")' in text
    assert "#heading(" not in text
    assert "#table(" not in text


def test_a_pin_on_a_net_counts_as_wired():
    """A pin with no wire but listed on a net is wired: heading and table (pdf-0039)."""
    text = _boards_model(("jb1",), on_net=True)

    assert "no pin wired" not in text
    assert "#table(" in text
