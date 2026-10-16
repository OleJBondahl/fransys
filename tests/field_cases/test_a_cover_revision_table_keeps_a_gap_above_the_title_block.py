"""Field case: the cover's revision table keeps a gap above the title block.

The engineering shape: a project on its fourth revision, so the cover carries a revision table of
four rows, and a cover with a short text.

The bug (v0.15): the table sits at the foot of the cover and its last row's bottom rule lies on
the title block's top rule, at 0.7 mm inside it. The two rules read as one thick line and the
oldest revision looks like a title block cell. The rule (decision pdf-0027): the revision table's
bottom rule lies at least 2 mm above the title block's top rule.
"""

lazy from pathlib import Path

import fransys as fr
import pypdfium2
from pypdfium2 import raw

_GAP_MM = 2
_POINTS_PER_MM = 72 / 25.4
_LAST_REVISION = 4

Box = tuple[float, float, float, float]


def _pdf(root: Path) -> Path:
    """The cabinet's PDF with four revisions: the cover only."""
    d = fr.design("demo_parts")
    d.project(
        title="Cabinet", number="CAB-1", customer="Demo Co", revision=_LAST_REVISION, author="d"
    )
    for number in range(1, _LAST_REVISION + 1):
        d.revision(number, date=f"2026-10-{10 + number}", text=f"Change {number}", created="XX")
    cabinet = d.location("C1", "Cabinet")
    d.terminal_strip("X1", "DEMO-TB-2.5", 3, place="C1")
    cover = root / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    document = fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=cover, remove=(fr.PageKind.SCHEMATIC,)
    )
    fr.write(fr.build(d, document), out_dir=root / "out", intermediates=root / "inter")
    (pdf,) = (root / "out").glob("*.pdf")
    return pdf


def _horizontal_rules(pdf: Path) -> tuple[float, list[Box], float]:
    """The cover's page width, its horizontal rule boxes, and the "Revision Date" header's left."""
    document = pypdfium2.PdfDocument(pdf)
    try:
        page = document[0]
        width, _ = page.get_size()
        text = page.get_textpage()
        header_left = text.get_charbox(text.get_text_range().index("Revision Date"))[0]
        rules = [
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
    table = [
        rule
        for rule in rules
        if rule[0] <= header_left <= rule[2]
        and rule[2] - rule[0] < 0.9 * width
        and rule[1] > title_top
    ]
    assert table
    gap_mm = (min(rule[1] for rule in table) - title_top) / _POINTS_PER_MM
    assert gap_mm >= _GAP_MM, f"the gap is {gap_mm:.2f} mm"
