"""Each schematic page carries a named destination that lands on that page (OVERVIEW O21).

The destination is read back from the compiled PDF with pypdfium2, so the check does not trust
the Typst source. The cover is page 0; the schematic pages follow in source order.
"""

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_raw
import pytest
import typst
from _build import document, drawing_set, layout_page, location, model, unit
from fransys_pdf import _drawings, font_dir, source

from fransys_model.derive import page_destination
from fransys_model.kernel import render_id
from fransys_model.vocab import DocumentPreset, PageKind

_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
    '<rect width="10" height="10"/></svg>'
)


def _fixture():
    c1 = location("C1", "First cabinet")
    c2 = location("C2", "Second cabinet")
    u = unit("u1", name="pump-cabinet")
    ds1 = drawing_set("ds1", location=c1, unit=u, number=1)
    ds2 = drawing_set("ds2", location=c2, unit=u, number=2)
    pages = (
        layout_page("a1", drawing_set=ds1, number=1),
        layout_page("a2", drawing_set=ds1, number=2),
        layout_page("b1", drawing_set=ds2, number=1),
        layout_page("b2", drawing_set=ds2, number=2),
    )
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=u,
        cover="# Cover",
        notes=None,
        remove=(PageKind.PLC_LIST, PageKind.TERMINAL_LIST, PageKind.BOM),
    )
    return model(c1, c2, u, ds1, ds2, *pages, doc), doc, pages


def _compile(m, doc, pages) -> bytes:
    svgs = {render_id(page.id): _SVG for page in pages}
    compiler = typst.Compiler(font_paths=[font_dir()], ignore_system_fonts=True)
    compiled = compiler.compile(input=source(m, doc.id, svgs).encode("utf-8"))
    assert isinstance(compiled, bytes)
    return compiled


def _page_index_of(pdf: pdfium.PdfDocument, name: str) -> int | None:
    dest = pdfium_raw.FPDF_GetNamedDestByName(pdf.raw, name.encode("utf-8"))
    if not dest:
        return None
    return pdfium_raw.FPDFDest_GetDestPageIndex(pdf.raw, dest)


def _assert_destinations(compiled: bytes, expected: dict[str, int]) -> None:
    pdf = pdfium.PdfDocument(compiled)
    assert len(pdf) == 1 + len(expected)  # the cover, then one page per schematic page
    for name, index in expected.items():
        assert _page_index_of(pdf, name) == index, name


def test_each_schematic_page_is_a_destination_on_its_own_page():
    m, doc, pages = _fixture()
    expected = {page_destination(m, page): 1 + i for i, page in enumerate(pages)}
    assert set(expected) == {"p1.1", "p1.2", "p2.1", "p2.2"}
    _assert_destinations(_compile(m, doc, pages), expected)


def test_a_swapped_label_fails_the_destination_check(monkeypatch):
    m, doc, pages = _fixture()
    expected = {page_destination(m, page): 1 + i for i, page in enumerate(pages)}
    first, second = pages[0], pages[1]
    swapped = {first.id: page_destination(m, second), second.id: page_destination(m, first)}
    monkeypatch.setattr(
        _drawings,
        "page_destination",
        lambda model, page: swapped.get(page.id, page_destination(model, page)),
    )
    compiled = _compile(m, doc, pages)
    with pytest.raises(AssertionError):
        _assert_destinations(compiled, expected)
