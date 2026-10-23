"""Viewer page labels (NV4): a sheet shows its sheet text, every other page its roman page number.

Labels and frame text are read back from the compiled PDF with pypdfium2. The frame's
"Page m of M" must stay the physical page and count although the labels set the page counter.
"""

import ctypes
import re

import fransys_render
import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_raw
import typst
from _build import document, drawing_set, layout_page, location, model, source, unit
from fransys_pdf._labels import sheet_label

from electrical_symbols import font_dir
from fransys_model.derive import document_sheets_of, page_destination, sheet_text
from fransys_model.kernel import make_id, render_id
from fransys_model.layout import DiagramSheet
from fransys_model.vocab import DocumentPreset, PageKind

_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
    '<rect width="10" height="10"/></svg>'
)
_NOTES = "\n\n".join(f"Paragraph {i}. " + "A long note sentence. " * 60 for i in range(12))
_ROMAN = ((10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i"))


def _roman(number: int) -> str:
    out = ""
    for value, digits in _ROMAN:
        count, number = divmod(number, value)
        out += digits * count
    return out


def _diagram(u, number: int) -> DiagramSheet:
    key = ("diagram_sheet", f"u1.{number}")
    return DiagramSheet(
        id=make_id(DiagramSheet, key), key=key, unit=u.id, number=number, produced_by="test"
    )


def _fixture():
    """Cover, flowing notes, index, B1, sheets 1, 2, 2.1, 2.2, then pages after the sheets."""
    c1 = location("C1", "First cabinet")
    u = unit("u1", name="pump-cabinet")
    ds1 = drawing_set("ds1", location=c1, unit=u, number=1)
    ds2 = drawing_set("ds2", location=c1, unit=u, number=2)
    pages = (
        layout_page("a1", drawing_set=ds1, number=1),
        layout_page("a2", drawing_set=ds1, number=2),
        layout_page("b1", drawing_set=ds2, number=1),
        layout_page("b2", drawing_set=ds2, number=2),
    )
    sheets = (_diagram(u, 1), *pages)
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=u,
        cover="# Cover",
        notes=_NOTES,
        add=(PageKind.BLOCK_DIAGRAM, PageKind.HARNESS_DRAWING),
    )
    return model(c1, u, ds1, ds2, *sheets, doc), doc, sheets


def _compile(m, doc, sheets) -> bytes:
    svgs = {render_id(sheet.id): _SVG for sheet in sheets}
    compiler = typst.Compiler(font_paths=[font_dir()], ignore_system_fonts=True)
    compiled = compiler.compile(
        input=source(m, doc.id, svgs, fransys_render.sheets(document_sheets_of(m))).encode("utf-8")
    )
    assert isinstance(compiled, bytes)
    return compiled


def _label(pdf: pdfium.PdfDocument, index: int) -> str:
    size = pdfium_raw.FPDF_GetPageLabel(pdf.raw, index, None, 0)
    buffer = (ctypes.c_ushort * (size // 2))()
    pdfium_raw.FPDF_GetPageLabel(pdf.raw, index, buffer, size)
    return bytes(buffer).decode("utf-16-le").rstrip("\0")


def _expected(pdf: pdfium.PdfDocument, m, sheets) -> list[str]:
    """Each sheet's text on the page its destination lands on; roman page numbers elsewhere."""
    out = [_roman(index + 1) for index in range(len(pdf))]
    for sheet in sheets:
        dest = pdfium_raw.FPDF_GetNamedDestByName(pdf.raw, page_destination(m, sheet).encode())
        out[pdfium_raw.FPDFDest_GetDestPageIndex(pdf.raw, dest)] = sheet_text(m, sheet)
    return out


def test_sheets_show_their_sheet_text_and_other_pages_their_roman_number():
    m, doc, sheets = _fixture()
    pdf = pdfium.PdfDocument(_compile(m, doc, sheets))
    labels = [_label(pdf, index) for index in range(len(pdf))]
    assert labels == _expected(pdf, m, sheets)
    assert {"B1", "1", "2", "2.1", "2.2"} <= set(labels)
    assert labels[-1] == _roman(len(pdf))  # the harness page after the sheets restarts roman
    assert len(set(labels)) == len(labels)


def test_every_frame_reads_its_physical_page_and_the_page_count():
    m, doc, sheets = _fixture()
    pdf = pdfium.PdfDocument(_compile(m, doc, sheets))
    assert len(pdf) == 10  # the notes flow onto pages 2 and 3, a counter step after a restart
    for index in range(len(pdf)):
        text = pdf[index].get_textpage().get_text_bounded()
        assert re.findall(r"(?<!\d)(\d+) of (\d+)", text) == [(str(index + 1), "10")], index


def test_the_same_model_gives_the_same_bytes_twice():
    m, doc, sheets = _fixture()
    assert _compile(m, doc, sheets) == _compile(m, doc, sheets)


def _sets_document(count: int):
    """`count` drawing sets of one page each, so sheet texts run `1`, `2.1`, ... `21.1`."""
    c1 = location("C1", "First cabinet")
    u = unit("u1", name="pump-cabinet")
    sets = tuple(drawing_set(f"ds{n}", location=c1, unit=u, number=n) for n in range(1, count + 1))
    pages = tuple(layout_page(f"p{n}", drawing_set=s, number=1) for n, s in enumerate(sets))
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=u, cover="# Cover")
    return model(c1, u, *sets, *pages, doc), doc, pages


def test_a_sheet_text_with_a_suffix_goes_whole_into_the_label_and_no_label_repeats():
    """21 sets: `10.3` style texts are written by Typst; `10.1`, `11.1`... take the roman label."""
    m, doc, pages = _sets_document(21)
    pdf = pdfium.PdfDocument(_compile(m, doc, pages))
    labels = [_label(pdf, index) for index in range(len(pdf))]
    assert len(set(labels)) == len(labels)
    by_text = {}
    for sheet in pages:
        dest = pdfium_raw.FPDF_GetNamedDestByName(pdf.raw, page_destination(m, sheet).encode())
        index = pdfium_raw.FPDFDest_GetDestPageIndex(pdf.raw, dest)
        by_text[sheet_text(m, sheet)] = (index, labels[index])
    assert by_text["9.1"][1] == "9.1"
    assert by_text["20.1"][1] == "20.1"
    for text in ("10.1", "11.1", "19.1", "21.1"):  # no split avoids a second counting symbol
        assert by_text[text][1] == _roman(by_text[text][0] + 1), text


def test_a_suffix_pattern_is_written_whole_by_typst():
    """`10.3` is pattern `1.3` on counter 10, the form the rule relies on."""
    for text, label in (("10.3", "10.3"), ("11.3", "11.3"), ("21.2", "21.2")):
        pattern, start = sheet_label(text)
        assert pattern == ', numbering: "1.' + text.split(".")[1] + '"'
        assert start == f"#counter(page).update({text.split('.')[0]})"
        source_text = (
            f"#set page(width: 50mm, height: 30mm)\n#page(margin: 0mm{pattern})[{start} x]"
        )
        pdf = pdfium.PdfDocument(typst.compile(source_text.encode()))
        assert _label(pdf, 0) == label
