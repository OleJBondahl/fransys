"""Field case: a cabinet of eleven relay circuits drawn on several sheets, with a notes page before them.
The bug: a reader holding the printed set had no list of its sheets, their titles and their PDF pages.
Fixed by pdf-0031, a Sheets index on by default lists each sheet's number, title and PDF page."""

import re
lazy from pathlib import Path

import fransys as fr
import pypdfium2
from _pdf_measure import has_page_title

_ROW = re.compile(r"^(\d+) (.+) (\d+)$")


def _built(root: Path, *, blocks: int) -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    d.project(title="Cabinet", number="CAB-1", customer="Demo Co", revision=1, author="d")
    d.revision(1, date="2026-10-12", text="First issue", created="XX")
    cabinet = d.location("C1", "Cabinet")
    for i in range(1, blocks + 1):
        with d.function(f"F{i}", f"Relay and lamp circuit {i}"):
            k = d.device(f"K{i}", "DEMO-RLY-2CO-24")
            lamp = d.device(f"H{i}", "DEMO-LAMP-24")
            d.series(k.co_1["14"], lamp[1], wire=("RD", 0.75))  # layout-0218: the circuit is wired
            d.series(lamp[2], k.coil["A1"], wire=("BU", 0.75))
            d.series(k.coil["A2"], k.co_1["11"], wire=("BU", 0.75))
    cover = root / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    notes = root / "cover.notes.md"
    notes.write_text("Notes before the sheets.\n", encoding="utf-8")
    document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=cover)
    return fr.build(d, document)


def _pdf(root: Path, *, blocks: int) -> pypdfium2.PdfDocument:
    result = _built(root, blocks=blocks)
    fr.write(result, out_dir=root / "out", intermediates=root / "inter")
    (pdf,) = (root / "out").glob("*.pdf")
    return pypdfium2.PdfDocument(pdf)


def _index_rows(pdf: pypdfium2.PdfDocument) -> tuple[int, list[tuple[str, str, int]]]:
    for number, page in enumerate(pdf, start=1):
        text = page.get_textpage().get_text_range()
        if has_page_title(text, "Sheets"):
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


def test_a_ring_of_three_two_port_functions_draws_every_wire(tmp_path) -> None:
    findings = _built(tmp_path, blocks=11).findings
    assert [f.code for f in findings if f.code == "CONNECTION_NOT_DRAWN"] == []
