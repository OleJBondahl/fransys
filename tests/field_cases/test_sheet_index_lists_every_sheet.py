"""Field case: a document of several sheets opens its drawings with a "Sheets" index.

The engineering shape: a cabinet of eleven relay circuits ("Relay and lamp circuit 1" to "... 11")
that draw on several sheets, with a notes page before them.

The bug: a reader holding the printed set had no list of its sheets, their titles and where each
sits in the PDF. The index is on by default (a "Sheets" page after the notes); one row per sheet
carries the sheet number, the title the sheet prints and the PDF page it is on. A document with one
sheet prints no index. The Page cell is Typst's physical page at the sheet's label, so notes that
overflow onto more pages move the cells with the sheets.

The decision that fixed it: pdf-0031.
"""

import re
lazy from pathlib import Path

import fransys as fr
import pypdfium2

_ROW = re.compile(r"^(\d+) (.+) (\d+)$")


def _pdf(root: Path, *, blocks: int) -> pypdfium2.PdfDocument:
    d = fr.design("demo_parts", place="C1")
    d.project(title="Cabinet", number="CAB-1", customer="Demo Co", revision=1, author="d")
    d.revision(1, date="2026-10-12", text="First issue", created="XX")
    cabinet = d.location("C1", "Cabinet")
    for i in range(1, blocks + 1):
        with d.function(f"F{i}", f"Relay and lamp circuit {i}"):
            k = d.device(f"K{i}", "DEMO-RLY-2CO-24")
            lamp = d.device(f"H{i}", "DEMO-LAMP-24")
            d.wire(k.co_1["14"], lamp[1], wire=("RD", 0.75))  # layout-0218: the circuit is wired
    cover = root / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    notes = root / "cover.notes.md"
    notes.write_text("Notes before the sheets.\n", encoding="utf-8")
    document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=cover)
    result = fr.build(d, document)
    fr.write(result, out_dir=root / "out", intermediates=root / "inter")
    (pdf,) = (root / "out").glob("*.pdf")
    return pypdfium2.PdfDocument(pdf)


def _index_rows(pdf: pypdfium2.PdfDocument) -> tuple[int, list[tuple[str, str, int]]]:
    for number, page in enumerate(pdf, start=1):
        text = page.get_textpage().get_text_range()
        if "Page title\r\nSheets" in text:
            lines = text.rsplit("Sheet Title Page\r\n", 1)[1].splitlines()
            return number, [(m[1], m[2], int(m[3])) for line in lines if (m := _ROW.match(line))]
    return 0, []


def test_a_sheets_page_after_the_notes_lists_every_sheet_with_its_pdf_page(tmp_path) -> None:
    pdf = _pdf(tmp_path, blocks=11)
    index_page, rows = _index_rows(pdf)
    assert index_page == 3  # cover, notes, then the Sheets page
    assert rows[0][0] == "1"
    assert re.fullmatch(r"Relay and lamp circuit 1 to \d+", rows[0][1])
    assert [row[2] for row in rows] == list(range(4, 4 + len(rows)))
    assert len(rows) >= 2


def test_a_document_of_one_sheet_prints_no_index(tmp_path) -> None:
    assert _index_rows(_pdf(tmp_path, blocks=1)) == (0, [])
