"""Field case: terminal list tables stand in two columns of 40 % and fill them before a new page.

The engineering shape: a cabinet with a few terminal strips, so the terminal list has one short
table per strip, and a cabinet with enough long strips for the list to need more than one page.

The bug (v0.13 look): every table took the full content width, one strip to a page, so a list of
short tables was mostly white paper. The rule (decision pdf-0026): tables stack down the left
column, then down the right column, and a new page opens only when both columns are full.
"""

import re
lazy from pathlib import Path

import fransys as fr
import pypdfium2
from _pdf_measure import has_page_title

_HEADING = re.compile(r"X\d+\r\n")
_FOOT = 0.14  # the title block's share of the page height, from the bottom
_SIDE = 30  # the frame's side letters and top numbers, in points


def _pdf(root: Path, strips: int, terminals: int) -> Path:
    """The cabinet's PDF: `strips` strips of `terminals` terminals, the terminal list only."""
    d = fr.design("demo_parts")
    d.project(title="Cabinet", number="CAB-1", customer="Demo Co", revision=1, author="d")
    d.revision(1, date="2026-10-12", text="First issue", created="XX")
    cabinet = d.location("C1", "Cabinet")
    for number in range(1, strips + 1):
        d.terminal_strip(f"X{number}", "DEMO-TB-2.5", terminals, place="C1")
    cover = root / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    document = fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC,
        cabinet,
        cover=cover,
        add=(fr.PageKind.TERMINAL_LIST,),
        remove=(fr.PageKind.SCHEMATIC,),
    )
    fr.write(fr.build(d, document), out_dir=root / "out", intermediates=root / "inter")
    (pdf,) = (root / "out").glob("*.pdf")
    return pdf


def _list_pages(pdf: Path) -> list[tuple[float, list[tuple[float, float, str]], str]]:
    """Per terminal list page: its width, its body glyphs `(x, y, char)` and its text."""
    document = pypdfium2.PdfDocument(pdf)
    try:
        found = []
        for page in document:
            width, height = page.get_size()
            text = page.get_textpage()
            body = [
                (left, bottom, text.get_text_range(i, 1))
                for i in range(text.count_chars())
                for left, bottom, _, _ in [text.get_charbox(i)]
                if _SIDE < left < width - _SIDE and _FOOT * height < bottom < height - _SIDE
            ]
            if has_page_title(text.get_text_range(), "Terminal list"):
                found.append((width, body, text.get_text_range()))
        return found
    finally:
        document.close()


def _heading_places(pdf: Path) -> list[tuple[int, float, float]]:
    """Each strip heading as `(list page, x, y)`, in reading order."""
    document = pypdfium2.PdfDocument(pdf)
    try:
        places = []
        pages = [
            p
            for p in document
            if has_page_title(p.get_textpage().get_text_range(), "Terminal list")
        ]
        for number, page in enumerate(pages):
            text = page.get_textpage()
            for found in _HEADING.finditer(text.get_text_range()):
                left, bottom, _, _ = text.get_charbox(found.start())
                places.append((number, left, bottom))
        return places
    finally:
        document.close()


def test_two_short_tables_fill_the_left_column_first(tmp_path: Path) -> None:
    """Two strips of four terminals: one page, both headings in the left column, stacked."""
    pdf = _pdf(tmp_path, 2, 4)
    pages = _list_pages(pdf)
    assert len(pages) == 1
    ((page_width, body, _),) = pages
    (first, second) = _heading_places(pdf)
    assert first[0] == second[0] == 0
    assert first[1] == second[1] < page_width / 2
    assert second[2] < first[2]
    assert all(x < page_width / 2 for x, _, _ in body)


def test_a_long_list_opens_its_second_page_only_when_both_columns_are_full(
    tmp_path: Path,
) -> None:
    """Three strips of thirty terminals: page one holds a full left and a full right column."""
    pdf = _pdf(tmp_path, 3, 30)
    pages = _list_pages(pdf)
    assert len(pages) == 2
    width, body, _ = pages[0]
    left = [y for x, y, _ in body if x < width / 2]
    right = [y for x, y, _ in body if x > width / 2]
    assert left
    assert right
    assert abs(min(left) - min(right)) < 30  # both columns end within a row or two of the foot
    width_two, body_two, _ = pages[1]
    assert all(x < width_two / 2 for x, _, _ in body_two)
