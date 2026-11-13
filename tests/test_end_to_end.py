"""One root end-to-end test: author, build, write."""

import re
from typing import Any, NamedTuple

import fransys as fr
import fransys_render
import pypdfium2
import pytest
import typst
from _model_build_cover import unit_document
from _pdf_lists import source
from demo_designs import cabinet_design
from fransys.colours import BU
from fransys_author.design import Design
from fransys_el import symbol_kit
from fransys_el.placement_views import marker_boxes
from fransys_el.placement_widest import link_fit

from electrical_symbols import LIBRARY
from fransys_model.derive import (
    document_export_name,
    document_page_kinds,
    document_sheets_of,
    documents,
    page_title,
    pdf_page,
    position_at,
    scope_path,
)
from fransys_model.derive.document_sets import set_printers
from fransys_model.derive.frame_position import row_letter
from fransys_model.derive.marker_targets import more_text
from fransys_model.kernel import render_id
from fransys_model.layout import DrawingSet, Page, layout_of, sheet_format_of

# `/Type /Page` but not `/Type /Pages` (the page tree root) or `/Type /PageLabel` (NV4) --
# confirmed by compiling and inspecting a real PDF (plan `.fransys/sdd-plan-pdf-stage2.md`, Task 7).
_PDF_PAGE = re.compile(rb"/Type\s*/Page(?![A-Za-z])")

# A minimal valid SVG, sized to the house sheet's content box: enough
# for Typst to place and compile, standing in for the facade's page SVGs (still a
# scaffold) so a `SCHEMATIC` page can be compiled at all.
_STUB_DRAWING_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="400mm" height="257mm" viewBox="0 0 400 257"></svg>'


def test_author_build_write_produces_the_cabinet_exports(tmp_path):
    """Author, build and write a small cabinet: the pipeline produces its exports.

    `SCHEMATIC` is removed: `fransys_render` is still a scaffold, so a cabinet document
    that keeps its `SCHEMATIC` pages carries `DOCUMENT_NO_DRAWINGS` and does not export at
    """
    parts = fr.parts("demo_parts")
    d = Design(parts)
    d.project(
        title="End to end",
        number="E2E-1",
        customer="Demo Co",
        revision=1,
        author="demo",
    )
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    c1 = d.location("C1", "Demo cabinet")
    sup = d.group("SUP", "Supply")
    q1 = d.item("DEMO-MCB-C6", tag="Q1", at=c1, group=sup)
    k1 = d.item("DEMO-RLY-2CO-24", tag="K1", at=c1, group=sup)
    d.wiring(colour="BU", gauge="0.75")(q1.fn("element")["2"], k1.fn("coil")["A1"])
    d.net("0V", k1.fn("coil")["A2"], cls="power", potential="0V")
    d.net("P24", q1.fn("element")["1"], cls="power", potential="+24V")

    cover = tmp_path / "cabinet.md"
    cover.write_text("# Demo cabinet\n", encoding="utf-8")
    document_draft = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, c1, cover=cover)

    result = fr.build(parts, d.draft(), document_draft)
    written = fr.write(result, tmp_path / "out")

    assert any(path.name == "E2E-1-v1.1-bom.csv" for path in written)
    assert any(path.name == "E2E-1-v1.1-overview.html" for path in written)
    pdfs = [path for path in written if path.suffix == ".pdf"]
    assert len(pdfs) == 1
    assert pdfs[0].read_bytes().startswith(b"%PDF-")


def test_document_pdf_has_the_expected_pages_and_embedded_font(demo_cabinet_document, tmp_path):
    """The demo cabinet document's PDF has one page per resolved `PageKind` and embeds the font.

    The acceptance bullet: "a page count equal to `document_page_kinds` expanded
    ... the DejaVu Sans family name in the bytes ... `<stem>.typ` in the intermediates
    """
    model = demo_cabinet_document.model
    (document_id,) = documents(model)
    pages = document_page_kinds(model, document_id)

    intermediates = tmp_path / "intermediates"
    written = fr.write(demo_cabinet_document, tmp_path / "out", intermediates=intermediates)

    pdfs = [path for path in written if path.suffix == ".pdf"]
    assert len(pdfs) == 1
    pdf_bytes = pdfs[0].read_bytes()
    assert pdf_bytes.startswith(b"%PDF-")

    # Every resolved page kind (COVER, NOTES, SCHEMATIC, PLC_LIST, TERMINAL_LIST, BOM here --
    # SCHEMATIC added by the render wiring; none of these holds enough
    # rows/pages to overflow onto a second physical page for this small demo cabinet) gives
    # exactly one `/Type /Page` object; pinned exactly, not a lower bound, because the
    # controller confirmed this same 6-kind shape against a real compiled PDF.
    # except PLC_LIST, CONNECTOR_LIST and SHEET_INDEX: no PLC channel, no connector and one sheet in
    # the demo cabinet, so those pages are left out (pdf-0019, the empty-list rule).
    assert fr.PageKind.PLC_LIST in pages
    assert fr.PageKind.CONNECTOR_LIST in pages
    assert fr.PageKind.SHEET_INDEX in pages
    assert len(_PDF_PAGE.findall(pdf_bytes)) == len(pages) - 3

    # Typst embeds the family as a subsetted PostScript name with no space.
    assert b"DejaVuSansCondensed" in pdf_bytes

    typ_files = list(intermediates.glob("*.typ"))
    assert len(typ_files) == 1

    # The page SVGs land in intermediates too (`_write_intermediates`,
    # `_file_safe`'s `:` -> `-`): one `layout.page-*.svg` per `layout.page` record of the
    # WHOLE model (the facade draws every page of the model) -- this cabinet lays out
    # two drawing sets (one at C1, one location-less), so two, not one; not scoped to just
    # this document's own schematic pages (`schematic_pages` returns only one of the two).
    render_svgs = list(intermediates.glob("layout.page-*.svg"))
    assert len(render_svgs) == len(layout_of(model, Page))
    typst.Compiler().compile(input=typ_files[0].read_bytes())


def test_document_pdf_is_byte_equal_on_a_second_write(demo_cabinet_document, tmp_path):
    """Writing the same built model twice gives byte-identical PDF bytes.

    It checks `source`/`write`'s determinism, not the pages' visual content.
    """
    first_written = fr.write(demo_cabinet_document, tmp_path / "out-1")
    second_written = fr.write(demo_cabinet_document, tmp_path / "out-2")

    first_pdfs = [path for path in first_written if path.suffix == ".pdf"]
    second_pdfs = [path for path in second_written if path.suffix == ".pdf"]
    assert len(first_pdfs) == 1
    assert len(second_pdfs) == 1

    first_bytes = first_pdfs[0].read_bytes()
    second_bytes = second_pdfs[0].read_bytes()
    assert len(first_bytes) > 0
    assert len(second_bytes) > 0
    assert first_bytes == second_bytes


def test_every_page_carries_the_frame_including_a_drawing_page(tmp_path):
    """Every page carries the project number and `n of N`.

    `fransys_render` is still a scaffold (`NotImplementedError`), so this cannot go
    through `fr.write`: it calls `fransys_pdf.source` directly with a stand-in SVG for
    """
    parts = fr.parts("demo_parts")
    design = cabinet_design(parts)
    c1 = Design(parts).location("C1", "Demo cabinet")
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Demo cabinet\n", encoding="utf-8")
    (tmp_path / "cabinet.notes.md").write_text("Some notes.\n", encoding="utf-8")
    document_draft = fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC,
        c1,
        cover=cover,
    )
    result = fr.build(parts, design.draft(), document_draft)
    model = result.model
    (document_id,) = documents(model)
    pages = document_page_kinds(model, document_id)
    assert fr.PageKind.SCHEMATIC in pages

    drawing_set = next(ds for ds in layout_of(model, DrawingSet).values() if ds.location == c1.id)
    drawing_pages = [page for page in layout_of(model, Page).values() if page.drawing_set == drawing_set.id]
    assert drawing_pages  # the cabinet design places symbols at C1, so layout drew a page
    svgs = {render_id(page.id): _STUB_DRAWING_SVG for page in drawing_pages}

    text = source(
        model,
        document_id,
        svgs,
        fransys_render.sheets(document_sheets_of(model, ()), LIBRARY),
    )
    typst.compile(input=text.encode())  # compiles on its own: proves it's a real document

    number = ">DEMO-1</text>"  # the project number (project.number), drawn in the title block
    assert number in text

    blocks = text.split("\n#pagebreak()\n")
    assert len(blocks) == 5  # COVER, NOTES, SCHEMATIC (one page), TERMINAL_LIST, BOM
    drawing_blocks = [block for block in blocks if "#image(bytes(" in block]
    assert len(drawing_blocks) == 1  # covers a drawing page specifically, not only list pages
    for index, block in enumerate(blocks, start=1):
        assert number in block, f"page {index} carries no project number"
        assert "<fransys-page-counter>" in block, f"page {index} carries no document counter"


_CITE = re.compile(r"#(\d+)-(.*?)p(\d+):\d+[A-Z]")


def _pdf_page_texts(path):
    """The text of each page of the PDF at `path`."""
    pdf = pypdfium2.PdfDocument(path)
    return [page.get_textpage().get_text_range() for page in pdf]


def _two_documents(root):
    """A cabinet and a field location, each its own document, with references from one into the other."""
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Docs", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-15", text="First issue", created="XX")
    cab, fld = d.location("CAB", "Cabinet"), d.location("FLD", "Field")
    psu, q = d.device("T1", "DEMO-PSU-24"), d.device("Q1", "DEMO-CTR-3P-NC")
    block = d.device(None, "DEMO-CTR-BLOCK-1NO1NC", name="blk", parent=q, place="FLD")
    lamp = d.device("P1", "DEMO-LAMP-24", place="FLD")
    wire = (BU, 0.5)
    for a, b in [(psu.output["+"], q.coil["A1"]), (psu.output["-"], q.coil["A2"]), (psu.output["+"], q.aux["13"])]:
        d.series(a, b, wire=wire)
    for a, b in [(q.aux["14"], lamp["1"]), (psu.output["-"], lamp["2"]), (lamp["1"], block.no["53"]), (block.no["54"], lamp["2"])]:
        d.series(a, b, wire=wire)
    (root / "c.md").write_text("# Docs\n", encoding="utf-8")
    cabinet = fr.DocumentPreset.CABINET_SCHEMATIC
    return fr.build(d, fr.document(cabinet, cab, cover=root / "c.md"), fr.document(cabinet, fld, cover=root / "c.md"))


def _pdf_texts(result, root):
    """Each document's PDF text per page, by the document's `scope_path`."""
    fr.write(result, root)
    model = result.model
    return {scope_path(model, record.id): _pdf_page_texts(root / document_export_name(model, None, record)) for record in documents(model).values()}


class _Io(NamedTuple):
    X1: Any


@fr.unit("demo-flags", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB", title="Flags", number="F-1")
def _flags(d: Any) -> _Io:
    """Twelve circuits sharing two strips: their reference flags cite other pages (the field case of the `+n` flag)."""
    x1 = d.terminal_strip("X" + "W" * 20, "DEMO-TB-2.5", 8, interface=True)
    x2 = d.terminal_strip("Y" + "W" * 20, "DEMO-TB-2.5", 8)
    hub: Any = None
    ends: dict[Any, Any] = {}
    for i in range(40):
        with d.function(f"C{i + 1:02d}", f"Circuit {i + 1}"):
            k = d.device(f"K{i + 1}", "DEMO-RLY-2CO-24")
            h = d.device(f"H{i + 1}", "DEMO-LAMP-24")
            d.series(ends.get(("x1", i % 6), x1[1 + i % 6].inner), k.coil["A1"], wire=("RD", 0.75))
            if hub is None:
                hub = k
            else:
                d.series(hub.coil["A2"], k.coil["A2"], wire=("BK", 0.75))
            d.series(ends.get(("x2", i % 6), x2[1 + i % 6].inner), k.co_1["11"], wire=("RD", 0.75))
            d.series(k.co_1["14"], h.lamp[1], wire=("RD", 0.75))
            d.series(h.lamp[2], ends.get("lamp", x2[8].inner), wire=("BU", 0.75))
            ends[("x1", i % 6)], ends[("x2", i % 6)], ends["lamp"] = k.coil["A1"], k.co_1["11"], h.lamp[2]
    return _Io(x1)


@pytest.mark.rule("PAGE-NUMBER")
def test_a_cited_page_is_the_pdf_page_that_holds_its_partner(tmp_path):
    """Each cut tag cites `p<n>`, and the partner tag with the same `#net` stands on page n of the compiled PDF (cover = 1)."""
    d = fr.design("demo_parts")
    d.add(_flags, "U1")
    ((_, pages),) = _pdf_texts(fr.build(d, unit_document("demo-flags")), tmp_path).items()
    cites = [(net, int(cited)) for text in pages for net, prefix, cited in _CITE.findall(text)]
    assert len(cites) >= 2, "the cut chain cites its other columns"
    assert all(f"#{net}-" in pages[cited - 1] for net, cited in cites)


@pytest.mark.rule("PAGE-NUMBER")
def test_a_reference_into_another_pdf_names_that_document_and_its_page(tmp_path):
    """The contact block in the field document cites the coil in the cabinet's PDF: the far document's text, then the page that holds the coil."""
    result = _two_documents(tmp_path)
    model = result.model
    texts = _pdf_texts(result, tmp_path / "out")
    pages = layout_of(model, Page)
    cab = next(p for p in pages.values() if scope_path(model, set_printers(model)[p.drawing_set]) == "+CAB" and p.number == 1)
    fld = next(p for p in pages.values() if scope_path(model, set_printers(model)[p.drawing_set]) == "+FLD" and p.number == 1)
    text = position_at(model, cab, fld, 1, "A")
    assert text == f"+FLD p{pdf_page(model, fld)}:1A"
    assert page_title(model, fld) in texts["+FLD"][pdf_page(model, fld) - 1]


@pytest.mark.rule("PAGE-NUMBER")
def test_every_printed_position_fits_the_marker_box_placement_reserves(tmp_path):
    """`link_fit` is as wide as `#n-<position>` for every page pair of one drawing set, cell and `+k` form (R2066)."""
    model = _two_documents(tmp_path).model
    reserved = link_fit(model, symbol_kit(model, LIBRARY), LIBRARY, None)["R0"].w
    pages = tuple(layout_of(model, Page).values())
    lines = [
        f"#{len(pages)}-{position_at(model, own, partner, column, row_letter(row))}{more_text(9)}"
        for own in pages
        for partner in pages
        if partner.drawing_set == own.drawing_set
        for column in range(1, sheet_format_of(model, partner.sheet_format).frame_columns + 1)
        for row in range(sheet_format_of(model, partner.sheet_format).frame_rows)
    ]
    assert max(marker_boxes(LIBRARY, line)["R0"].w for line in lines) <= reserved
