"""Field case: a continued terminal list prints its heading clear of its table.

The engineering shape: one terminal strip long enough that its list flows past a column foot.
The bug: the continued heading ("-X1 (cont.)") sat in the table's header cell with no spacing, so
its letters ran onto the table's top border, while the first fragment's heading stood clear.
The fix (pdf-0053 spacing): an empty block after the carried heading keeps the heading's own
below-spacing, which the cell's end would drop.
The rule (LISTS): a continued heading keeps the first heading's gap to its table.
"""

import tempfile
from functools import cache
from pathlib import Path

import fransys as fr
import pypdfium2 as pdfium

COUNT = 160
_HEADING_PT = 9  # a heading's letters stand taller than a table cell's


@cache
def _pdf() -> bytes:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G1", "Supply"):
        d.terminal_strip("X1", "DEMO-TB-2.5", COUNT)
    tmp = Path(tempfile.mkdtemp())
    cover = tmp / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    paths = fr.write(fr.build(d, doc), tmp / "out")
    return next(p for p in paths if p.suffix == ".pdf").read_bytes()


def _hits(text, needle: str) -> list[tuple[float, float, float, str]]:
    """(left, bottom, top, the character after it) in points of each hit of `needle`."""
    found = []
    search = text.search(needle)
    while hit := search.get_next():
        end = hit[0] + hit[1]
        boxes = [text.get_charbox(i) for i in range(hit[0], end)]
        found.append(
            (
                boxes[0][0],
                min(b[1] for b in boxes),
                max(b[3] for b in boxes),
                text.get_text_range(end, 1),
            )
        )
    return found


def _gaps() -> tuple[list[float], list[float]]:
    """Heading-to-table gaps in points: the first fragment's, then each continued heading's."""
    first, carried = [], []
    for page in pdfium.PdfDocument(_pdf()):
        text = page.get_textpage()
        tables = [(left, top) for left, _, top, _ in _hits(text, "Designation")]
        for left, bottom, top, after in _hits(text, "-X1"):
            if top - bottom > _HEADING_PT:
                # the table of its own column: the nearest header at or right of the heading
                _, table_top = min((t for t in tables if t[0] >= left - 1), key=lambda t: t[0])
                (carried if after == " " else first).append(bottom - table_top)
    return first, carried


def test_a_continued_heading_keeps_the_first_headings_gap_to_its_table():
    first, carried = _gaps()
    assert first, "no first-fragment heading found"
    assert carried, "the strip did not continue"
    assert min(carried) >= min(first) - 1.0, (first, carried)
