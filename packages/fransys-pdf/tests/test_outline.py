"""The PDF outline: one entry per sheet, landing on its page, whatever is printed before it (NV3).

A notes text of many pages pushes the sheets down; each entry must still land on its own page.
The PDF is read back with pypdfium2, not the Typst source.
"""

import fransys_render
import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_raw
import pytest
import typst
from _build import document, drawing_set, layout_page, location, model, source, unit

from electrical_symbols import LIBRARY, font_dir
from fransys_model.derive import document_sheets_of, page_destination
from fransys_model.kernel import render_id
from fransys_model.vocab import DocumentPreset, PageKind

_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
    '<rect width="10" height="10"/></svg>'
)


def _compiled(notes: str | None) -> tuple[bytes, list[str]]:
    cabinet = location("C1", "First cabinet")
    u = unit("u1", name="pump-cabinet")
    ds1 = drawing_set("ds1", location=cabinet, unit=u, number=1)
    pages = (
        layout_page("a1", drawing_set=ds1, number=1),
        layout_page("a2", drawing_set=ds1, number=2),
    )
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=u,
        cover="# Cover",
        notes=notes,
        remove=(PageKind.PLC_LIST, PageKind.TERMINAL_LIST, PageKind.BOM),
    )
    m = model(cabinet, u, ds1, *pages, doc)
    svgs = {render_id(page.id): _SVG for page in pages}
    compiler = typst.Compiler(font_paths=[font_dir()], ignore_system_fonts=True)
    compiled = compiler.compile(
        input=source(m, doc.id, svgs, fransys_render.sheets(document_sheets_of(m), LIBRARY)).encode(
            "utf-8"
        )
    )
    assert isinstance(compiled, bytes)
    return compiled, [page_destination(m, page) for page in pages]


def _landing(pdf: pdfium.PdfDocument, name: str) -> int:
    dest = pdfium_raw.FPDF_GetNamedDestByName(pdf.raw, name.encode("utf-8"))
    return pdfium_raw.FPDFDest_GetDestPageIndex(pdf.raw, dest)


@pytest.mark.parametrize("notes_pages", [0, 16])
def test_each_sheet_entry_lands_on_its_sheet_in_sheet_order(notes_pages: int) -> None:
    notes = "\n\n".join("Notes line. " * 150 for _ in range(notes_pages)) or "Short."
    compiled, destinations = _compiled(notes)
    pdf = pdfium.PdfDocument(compiled)
    toc = [(b.level, b.get_title(), b.get_dest().get_index()) for b in pdf.get_toc()]
    sheets = [entry for entry in toc if entry[1].startswith("Sheet ")]
    assert [entry[1].split(":")[0] for entry in sheets] == ["Sheet 1", "Sheet 2"]
    assert [entry[2] for entry in sheets] == [_landing(pdf, name) for name in destinations]
    assert sheets[0][2] > (2 if notes_pages else 0)  # notes pages come before the sheets
