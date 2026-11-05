"""Field case: a 370-character notice fits the title block's notice cell on the A3 house frame.
The bug (v0.18.5): the cell held fewer lines than the legend wraps to, and the check counted at an unused pitch.
Fixed by pdf-0038, the cell is about 92 mm wide with a notice, and the check counts the lines the PDF shows."""

from typing import Any
lazy from pathlib import Path

import fransys as fr
import pypdfium2

_WORDS = "This drawing is the property of Demo Co and may not be copied or shown to a third party"
_LEGEND = " ".join([_WORDS] * 4) + " Demo Co ENDING"  # 366 characters, the last word distinctive
_LONG = " ".join([_WORDS] * 8) + " ENDING"  # about 600 characters
_POINTS_PER_MM = 72 / 25.4
_FRAME_MM = 5
assert 360 <= len(_LEGEND) <= 370


def _build(root: Path, notice: str, *, customer: str = "Demo Co", author: str = "d"):
    root.mkdir(parents=True, exist_ok=True)
    d = fr.design("demo_parts", place="C1")
    d.project(title="Cabinet", number="CAB-1", customer=customer, revision=1, author=author)
    d.revision(1, date="2026-10-11", text="First issue", created="XX")
    cabinet = d.location("C1", "Cabinet")
    d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    cover = root / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    document = fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC,
        cabinet,
        cover=cover,
        notice=notice,
    )
    result = fr.build(d, document)
    fr.write(result, out_dir=root / "out", intermediates=root / "inter")
    (pdf,) = (root / "out").glob("*.pdf")
    return result, pdf


def _ending_bottom_mm(pdf: Path) -> Any:
    """The bottom (mm up from the page foot) of the last word's first letter on page 1.

    A clipped line stays in the text layer, so the word's position says whether it was drawn
    inside the frame (the frame lies 5 mm inside the page edge).
    """
    document = pypdfium2.PdfDocument(pdf)
    try:
        textpage = document[0].get_textpage()
        start, count = textpage.search("ENDING").get_next()
        assert count == len("ENDING")
        return textpage.get_charbox(start)[1] / _POINTS_PER_MM
    finally:
        document.close()


def _codes(result) -> list[str]:
    return [f.code for f in fr.check(result)]


def test_a_370_character_notice_prints_whole_with_no_finding(tmp_path):
    result, pdf = _build(tmp_path, _LEGEND)
    assert "TITLE_BLOCK_NOTICE_OVERFLOW" not in _codes(result)
    assert _ending_bottom_mm(pdf) >= _FRAME_MM


def test_a_600_character_notice_gives_the_finding(tmp_path):
    result, _pdf = _build(tmp_path, _LONG)
    assert "TITLE_BLOCK_NOTICE_OVERFLOW" in _codes(result)


def _filler(count: int) -> str:
    return " ".join(["alpha"] * count) + " ENDING"


def test_the_last_line_the_check_counts_is_a_line_the_pdf_shows(tmp_path):
    """The longest filler the check passes has its last word inside the frame (pdf-0038 NC3)."""
    low, high = 30, 200  # `_filler(low)` passes the check, `_filler(high)` does not
    while high - low > 1:
        mid = (low + high) // 2
        result, _pdf = _build(tmp_path / f"b{mid}", _filler(mid))
        if "TITLE_BLOCK_NOTICE_OVERFLOW" in _codes(result):
            high = mid
        else:
            low = mid
    _result, pdf = _build(tmp_path / "last", _filler(low))
    assert _ending_bottom_mm(pdf) >= _FRAME_MM
