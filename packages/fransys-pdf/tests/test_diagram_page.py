"""BLOCK_DIAGRAM pages (BD7, acceptance 10, pdf-0023): one A2 page per `DiagramSheet`.

The model holds hand-built `DiagramSheet` records, the only part of the layout result pdf
reads, so no layout package is imported. The compiled PDF's `/MediaBox` entries give the
page sizes: the diagram page is 594 x 420 mm, every other page stays on the house A3.
"""

import re
import zlib

import typst
from _build import document, location, model, project, unit
from fransys_pdf import PRESET_PAGES, document_pages, page_kinds, source
from fransys_pdf._frame import TitleBlockFields, background
from fransys_pdf._geometry import document_facts, project_notice, subject_label

from fransys_model.kernel import make_id, render_id
from fransys_model.layout import DiagramSheet, a2_sheet_format, default_sheet_format
from fransys_model.vocab import DocumentPreset, PageKind, documents

K = PageKind
_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="584mm" height="390mm"></svg>'
_PT_PER_MM = 72 / 25.4


def _sheet(number: int, *, unit_id=None) -> DiagramSheet:
    key = ("diagram-sheet", str(unit_id), str(number))
    return DiagramSheet(
        id=make_id(DiagramSheet, key), key=key, unit=unit_id, number=number, produced_by="test"
    )


def _system(sheets: int, *, add: tuple[PageKind, ...] = ()):
    """A SYSTEM document and a model with `sheets` absolute diagram sheets."""
    doc = document("d1", preset=DocumentPreset.SYSTEM, cover="# Cover", notes="Notes.", add=add)
    records = [_sheet(number) for number in range(1, sheets + 1)]
    return doc, model(project(), doc, *records), records


def _svgs(records):
    return {render_id(record.id): _SVG for record in records}


def _media_boxes_mm(text: str) -> list[tuple[int, int]]:
    """The compiled pages' sizes in mm, rounded, in page order."""
    pdf = typst.compile(text.encode("utf-8"))
    # Typst packs the page dictionaries into compressed object streams: inflate every stream.
    plain = pdf
    for body in re.findall(rb"stream\r?\n(.*?)endstream", pdf, re.DOTALL):
        try:
            plain += zlib.decompressobj().decompress(body)
        except zlib.error:  # a stream that is not zlib (an image, a font) holds no page box
            continue
    boxes = re.findall(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", plain)
    assert boxes, "no /MediaBox found in the compiled PDF"
    return [(round(float(w) / _PT_PER_MM), round(float(h) / _PT_PER_MM)) for w, h in boxes]


def test_system_source_has_one_a2_page_per_sheet_with_the_a2_frame_in_its_background():
    doc, m, records = _system(2)
    text = source(m, doc.id, _svgs(records))
    assert text.count("#page(width: 594mm, height: 420mm, margin: 0mm") == 2
    record = documents(m)[doc.id]
    fields = TitleBlockFields(
        *document_facts(m, record),
        page_title="Block diagram",
        scope=subject_label(m, record),
        sheet_counter="2 / 2",
        notice=project_notice(m),
        logo=record.logo,
    )
    assert background(a2_sheet_format(), fields) in text
    assert background(default_sheet_format(), fields) not in text


def test_the_compiled_diagram_page_is_a2_and_every_other_page_stays_a3():
    """The acceptance-10 probe target: a diagram drawn on the house A3 fails here."""
    doc, m, records = _system(1, add=(K.SCHEMATIC,))
    sizes = _media_boxes_mm(source(m, doc.id, _svgs(records)))
    assert sizes == [(420, 297), (420, 297), (594, 420), (420, 297)]


def test_the_diagram_page_comes_after_cover_and_notes_and_before_the_rest():
    doc, m, _ = _system(1)
    pages = document_pages(m, doc.id)
    assert pages[:3] == (K.COVER, K.NOTES, K.BLOCK_DIAGRAM)
    assert pages == page_kinds(DocumentPreset.SYSTEM)
    assert PRESET_PAGES[DocumentPreset.SYSTEM][2] is K.BLOCK_DIAGRAM


def test_a_page_per_sheet_in_number_order_with_its_own_counter():
    doc, m, records = _system(2)
    text = source(m, doc.id, _svgs(records))
    assert text.index("1 / 2") < text.index("2 / 2")
    assert _media_boxes_mm(text)[2:] == [(594, 420), (594, 420)]


def test_a_sheet_without_an_svg_is_left_out():
    doc, m, records = _system(2)
    text = source(m, doc.id, _svgs(records[:1]))
    assert text.count("#page(width: 594mm") == 1


def test_a_reading_with_no_sheet_gives_no_page_and_no_placeholder():
    doc, m, _ = _system(0)
    text = source(m, doc.id, {})
    assert "594mm" not in text
    assert "#pagebreak()\n#pagebreak()" not in text


def test_an_unmounted_document_has_no_diagram_section_and_add_gives_it_one():
    c1 = location("C1", "Demo cabinet")
    plain = document(
        "d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=c1, cover="# Cover", notes=None
    )
    plain_pages = page_kinds(DocumentPreset.CABINET_SCHEMATIC)
    assert K.BLOCK_DIAGRAM not in plain_pages
    m = model(project(), c1, plain)
    assert "594mm" not in source(m, plain.id, {})


def test_a_unit_document_with_add_draws_its_own_unit_sheets_only():
    u = unit("u1", name="demo-board")
    other = unit("u2", name="demo-other")
    doc = document(
        "d1",
        preset=DocumentPreset.PCB_SCHEMATIC,
        subject=u,
        cover="# Cover",
        add=(K.BLOCK_DIAGRAM,),
    )
    mine, theirs, absolute = _sheet(1, unit_id=u.id), _sheet(1, unit_id=other.id), _sheet(1)
    m = model(project(), u, other, doc, mine, theirs, absolute)
    svgs = _svgs([mine, theirs, absolute])
    assert K.BLOCK_DIAGRAM in documents(m)[doc.id].add
    assert source(m, doc.id, svgs).count("#page(width: 594mm") == 1
