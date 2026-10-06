"""One root end-to-end test: author, build, write (spec section 10, facade spec F9)."""

import re

import fransys as fr
import fransys_author
import typst
from demo_designs import cabinet_design
from fransys_pdf import document_pages, source

from fransys_model.kernel.ids import render_id
from fransys_model.layout import DrawingSet, Page, layout_of
from fransys_model.vocab import documents

# `/Type /Page` but not `/Type /Pages` (the page tree root) -- confirmed by compiling and
# inspecting a real PDF (plan `.fransys/sdd-plan-pdf-stage2.md`, Task 7).
_PDF_PAGE = re.compile(rb"/Type\s*/Page(?!s)")

# A minimal valid SVG, sized to the house sheet's content box (page-frame spec R4): enough
# for Typst to place and compile, standing in for `fransys_render.pages` (still a
# scaffold, spec P11) so a `SCHEMATIC` page can be compiled at all.
_STUB_DRAWING_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="400mm" height="257mm" '
    'viewBox="0 0 400 257"></svg>'
)


def test_author_build_write_produces_the_cabinet_exports(tmp_path):
    """Author, build and write a small cabinet: the pipeline produces its exports.

    `SCHEMATIC` is removed: `fransys_render` is still a scaffold, so a cabinet document
    that keeps its `SCHEMATIC` pages carries `DOCUMENT_NO_DRAWINGS` and does not export at
    all (decision 0011, pdf spec P11). The fuller PDF assertion (page count, font family,
    byte-equality) is a separate, later task's job.
    """
    parts = fr.parts("demo_parts")
    d = fransys_author.Design(parts)
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

    cover = tmp_path / "cabinet.md"
    cover.write_text("# Demo cabinet\n", encoding="utf-8")
    document_draft = fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC, c1, cover=cover, remove=(fr.PageKind.SCHEMATIC,)
    )

    result = fr.build(parts, d.draft(), document_draft)
    written = fr.write(result, tmp_path / "out")

    assert any(path.name == "E2E-1-v1.1-bom.csv" for path in written)
    assert any(path.name == "E2E-1-v1.1-overview.html" for path in written)
    pdfs = [path for path in written if path.suffix == ".pdf"]
    assert len(pdfs) == 1
    assert pdfs[0].read_bytes().startswith(b"%PDF-")


def test_document_pdf_has_the_expected_pages_and_embedded_font(demo_cabinet_document, tmp_path):
    """The demo cabinet document's PDF has one page per resolved `PageKind` and embeds the font.

    Spec P13's acceptance bullet: "a page count equal to `document_pages` expanded per P10
    ... the Liberation Serif family name in the bytes ... `<stem>.typ` in the intermediates
    that compiles on its own." Byte-equality on a second write is the separate test below.
    """
    model = demo_cabinet_document.model
    (document_id,) = documents(model)
    pages = document_pages(model, document_id)

    intermediates = tmp_path / "intermediates"
    written = fr.write(demo_cabinet_document, tmp_path / "out", intermediates=intermediates)

    pdfs = [path for path in written if path.suffix == ".pdf"]
    assert len(pdfs) == 1
    pdf_bytes = pdfs[0].read_bytes()
    assert pdf_bytes.startswith(b"%PDF-")

    # Every resolved page kind (COVER, NOTES, SCHEMATIC, PLC_LIST, TERMINAL_LIST, BOM here --
    # SCHEMATIC added by the render work package's wiring, PART 5; none of these holds enough
    # rows/pages to overflow onto a second physical page for this small demo cabinet) gives
    # exactly one `/Type /Page` object; pinned exactly, not a lower bound, because the
    # controller confirmed this same 6-kind shape against a real compiled PDF.
    # except PLC_LIST: no PLC channel in the demo cabinet, so that page is left out (pdf-0019).
    assert fr.PageKind.PLC_LIST in pages
    assert len(_PDF_PAGE.findall(pdf_bytes)) == len(pages) - 1

    # Typst embeds the family as a subsetted PostScript name with no space.
    assert b"LiberationSerif" in pdf_bytes

    typ_files = list(intermediates.glob("*.typ"))
    assert len(typ_files) == 1

    # The render work package's page SVGs land in intermediates too (`_write_intermediates`,
    # `_file_safe`'s `:` -> `-`): one `layout.page-*.svg` per `layout.page` record of the
    # WHOLE model (`fransys_render.pages`' own contract, spec P1) -- this cabinet lays out
    # two drawing sets (one at C1, one location-less), so two, not one; not scoped to just
    # this document's own schematic pages (`schematic_pages` returns only one of the two).
    render_svgs = list(intermediates.glob("layout.page-*.svg"))
    assert len(render_svgs) == len(layout_of(model, Page))
    typst.Compiler().compile(input=typ_files[0].read_bytes())


def test_document_pdf_is_byte_equal_on_a_second_write(demo_cabinet_document, tmp_path):
    """Writing the same built model twice gives byte-identical PDF bytes (spec P1, P13).

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
    """Page-frame spec acceptance 1: every page carries the project number and `n of N`.

    `fransys_render` is still a scaffold (`NotImplementedError`), so this cannot go
    through `fr.write`: it calls `fransys_pdf.source` directly with a stand-in SVG for
    the cabinet's one real `SCHEMATIC` page (from `fransys_layout`'s actual output, not a
    hand-built fixture), the same substitution `test_golden.py` and this package's own tests
    already make for a page's drawing. `typst.query` cannot help verify the rendered
    `n of N` text: it returns Typst's `context` nodes unevaluated (probed directly against
    this package's compiled source, not assumed), and no PDF-text-extraction library is
    installed or addable here (root CLAUDE.md: no new dependency without asking). The proof
    is source-structural instead, split on the exact `#pagebreak()` separator `source` itself
    joins pages with, so each element of the split is one physical page's own Typst block in
    page order -- equally strict against the trap: the background carrying the project
    number and the `<fransys-page-counter>`-labelled document counter is only present on
    a block when that block's own `#page`/`#set page` call actually names `background:`.
    """
    parts = fr.parts("demo_parts")
    design = cabinet_design(parts)
    c1 = fransys_author.Design(parts).location("C1", "Demo cabinet")
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Demo cabinet\n", encoding="utf-8")
    (tmp_path / "cabinet.notes.md").write_text("Some notes.\n", encoding="utf-8")
    document_draft = fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC,
        c1,
        cover=cover,
        remove=(fr.PageKind.PLC_LIST, fr.PageKind.TERMINAL_LIST, fr.PageKind.BOM),
    )
    result = fr.build(parts, design.draft(), document_draft)
    model = result.model
    (document_id,) = documents(model)
    pages = document_pages(model, document_id)
    assert fr.PageKind.SCHEMATIC in pages

    drawing_set = next(ds for ds in layout_of(model, DrawingSet).values() if ds.location == c1.id)
    drawing_pages = [
        page for page in layout_of(model, Page).values() if page.drawing_set == drawing_set.id
    ]
    assert drawing_pages  # the cabinet design places symbols at C1, so layout drew a page
    svgs = {render_id(page.id): _STUB_DRAWING_SVG for page in drawing_pages}

    text = source(model, document_id, svgs)
    typst.compile(input=text.encode())  # compiles on its own: proves it's a real document

    assert '"DEMO-1"' in text  # the project number (project.number, authored by `cabinet_design`)

    blocks = text.split("\n#pagebreak()\n")
    assert len(blocks) == 3  # COVER, SCHEMATIC (one page), NOTES
    drawing_blocks = [block for block in blocks if 'format: "svg"' in block]
    assert len(drawing_blocks) == 1  # covers a drawing page specifically, not only list pages
    for index, block in enumerate(blocks, start=1):
        assert '"DEMO-1"' in block, f"page {index} carries no project number"
        assert "<fransys-page-counter>" in block, f"page {index} carries no document counter"
