"""Field case: the cover's revision table keeps a gap above the title block.
The bug (v0.15): the table's last bottom rule lay 0.7 mm inside the title block's top rule, so the two read as one thick line.
Fixed by pdf-0027, the revision table's bottom rule lies at least 2 mm above the title block's top rule."""

from itertools import takewhile
from typing import Any, NamedTuple
lazy from pathlib import Path

import fransys as fr
import pypdfium2
import pytest
from _field_designs import written_pdf
from fransys.colours import BK
from pypdfium2 import raw

from fransys_model.derive import documents, drawn_pages, pdf_page

_GAP_MM = 2
_POINTS_PER_MM = 72 / 25.4
_LAST_REVISION = 4

Box = tuple[float, float, float, float]


def _pdf(root: Path) -> Path:
    """The cabinet's PDF with four revisions: the cover only."""
    d = fr.design("demo_parts")
    d.project(title="Cabinet", number="CAB-1", customer="Demo Co", revision=_LAST_REVISION, author="d")
    for number in range(1, _LAST_REVISION + 1):
        d.revision(number, date=f"2026-10-{10 + number}", text=f"Change {number}", created="XX")
    cabinet = d.location("C1", "Cabinet")
    d.terminal_strip("X1", "DEMO-TB-2.5", 3, place="C1")
    cover = root / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=cover)
    return written_pdf(fr.build(d, document), root)


def _horizontal_rules(pdf: Path) -> tuple[Any, list[Box], Any]:
    """The cover's page width, its horizontal rule boxes, and the "Revision Date" header's left."""
    document = pypdfium2.PdfDocument(pdf)
    try:
        page = document[0]
        width, _ = page.get_size()
        text = page.get_textpage()
        header_left = text.get_charbox(text.get_text_range().index("Revision Date"))[0]
        rules: list[Box] = [
            bounds
            for obj in page.get_objects()
            if obj.type == raw.FPDF_PAGEOBJ_PATH
            and (bounds := obj.get_bounds())[2] - bounds[0] > 20
            and bounds[3] - bounds[1] < 70  # a table rule, or the title block's outline
        ]
        return width, rules, header_left
    finally:
        document.close()


def test_the_revision_table_ends_two_millimetres_above_the_title_block(tmp_path: Path) -> None:
    """The gap from the table's bottom rule up to the title block's top rule is at least 2 mm."""
    width, rules, header_left = _horizontal_rules(_pdf(tmp_path))
    # the title block's top edge is the highest outline or rule that spans most of the page's
    # frame: the title block's outline (the square logo cell is its own outline) or a band rule
    spanning = [rule for rule in rules if rule[2] - rule[0] > 0.9 * width and rule[3] < width / 4]
    title_top = max(rule[3] for rule in spanning)
    # the table's rules cross its header column and lie at or above the title block's top rule
    table = [rule for rule in rules if rule[0] <= header_left <= rule[2] and rule[2] - rule[0] < 0.9 * width and rule[1] > title_top]
    assert table
    gap_mm = (min(rule[1] for rule in table) - title_top) / _POINTS_PER_MM
    assert gap_mm >= _GAP_MM, f"the gap is {gap_mm:.2f} mm"


class _Io(NamedTuple):
    M1: fr.Device


@pytest.mark.rule("COVER-REVISIONS")
@pytest.mark.parametrize(("rows", "paper"), [(3, "A3"), (18, "A3"), (40, "A3"), (3, "A2"), (18, "A2")])
def test_a_drawing_page_counts_every_cover_page_whatever_the_history_length(tmp_path: Path, rows: int, paper: str) -> None:
    """KI-985, R2334: a long cover flows over further pages; the stored front count equals the PDF's cover pages, at the document's paper."""
    history = [{"version": 1, "revision": n, "date": "2026-01-01", "text": f"Revision {n}: changed wiring", "created": "AB"} for n in range(1, rows)]

    @fr.unit(
        "starter", version=1, revision=rows, interface_version=1, date="2026-01-01", text=f"Revision {rows}: changed wiring", by="AB", history=history
    )
    def build(d: fr.Design) -> _Io:
        x0 = d.terminal_strip("X2", "DEMO-TB-2.5-TWIN")
        ac = d.ac_supply("400V", "230", x0[1], x0[2], x0[3], n=x0[4])
        q0, q1, f1 = d.device("Q2", "DEMO-MCB-3P"), d.device("Q1", "DEMO-CTR-3P-24"), d.device("F1", "DEMO-OVERLOAD-3P")
        x1 = d.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5")
        m1, w1 = d.device("M1", "DEMO-MOTOR-4KW"), d.cable("W1", "DEMO-CBL-4G1.5")
        d.series(ac, q0.element, q1.main, f1.main, x1, w1, m1, wire=(BK, 2.5))
        return _Io(M1=m1)

    d = fr.design("demo_parts")
    d.add(build, "U1")
    cover = tmp_path / "cover.md"
    cover.write_text("# Motor starter\n\nA starter.\n\n## Notes\n\n" + "- A generic note line.\n" * 18, encoding="utf-8")
    document_ = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "starter", cover=cover)
    result = fr.build(d, document_, settings=fr.settings(paper={fr.PageKind.SCHEMATIC: paper}))
    fr.write(result, out_dir=tmp_path / "out")
    (pdf,) = (tmp_path / "out").glob("*.pdf")
    (document,) = documents(result.model)
    first = next(iter(drawn_pages(result.model, document)))
    cover_pages = len(list(takewhile(lambda page: "Cover" in page.get_textpage().get_text_range(), pypdfium2.PdfDocument(pdf))))
    assert pdf_page(result.model, first) - 1 == cover_pages
    assert (cover_pages > 1) == (rows > 17 and paper == "A3")
