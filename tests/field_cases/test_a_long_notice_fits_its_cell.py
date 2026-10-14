"""Field case: a 370-character notice fits the title block's notice cell.

The engineering shape: a cabinet document with the IP legend a company prints on every sheet,
about 370 characters, on the A3 house frame.

The bug (v0.18.5): the notice cell is 43 mm wide, the legend wraps to more lines than the cell
holds, and the PDF cuts it off mid-sentence. The check counts lines at a pitch the drawing does
not use, so it is silent as well. The rule (decision pdf-0038): the cell is about 92 mm wide with a
notice, and the check counts the lines the PDF shows. Two tests build over a second each (a
bisection of documents, a title found by growing); their builds differ in the document, so they
cannot share one.
"""

lazy from pathlib import Path

import fransys as fr
import pypdfium2

_WORDS = "This drawing is the property of Demo Co and may not be copied or shown to a third party"
_LEGEND = " ".join([_WORDS] * 4) + " Demo Co ENDING"  # 366 characters, the last word distinctive
_LONG = " ".join([_WORDS] * 8) + " ENDING"  # about 600 characters
_POINTS_PER_MM = 72 / 25.4
_FRAME_MM = 5
assert 360 <= len(_LEGEND) <= 370


def _build(
    root: Path, notice: str, *, customer: str = "Demo Co", author: str = "d", page_title: str = ""
):
    root.mkdir(parents=True, exist_ok=True)
    d = fr.design("demo_parts", place="C1")
    d.project(title="Cabinet", number="CAB-1", customer=customer, revision=1, author=author)
    d.revision(1, date="2026-10-11", text="First issue", created="XX")
    cabinet = d.location("C1", "Cabinet")
    strip = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    if page_title:
        lamp = d.device("H1", "DEMO-LAMP-24")
        d.wire(strip.run("SIG", 1)[1], lamp.lamp["1"], wire=("WH", 0.75))
        d.layout.page_title(strip, page_title)
    cover = root / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    document = fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC,
        cabinet,
        cover=cover,
        remove=() if page_title else (fr.PageKind.SCHEMATIC,),
        notice=notice,
    )
    result = fr.build(d, document)
    fr.write(result, out_dir=root / "out", intermediates=root / "inter")
    (pdf,) = (root / "out").glob("*.pdf")
    return result, pdf


def _ending_bottom_mm(pdf: Path) -> float:
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


def _page_title_cuts(result) -> list[str]:
    return [f.message for f in fr.check(result) if f.code == "TITLE_BLOCK_TEXT_OVERFLOW"]


def test_a_notice_cuts_no_page_title_or_one_line_field_that_fitted(tmp_path):
    """The width comes from Customer and Author; the Page title keeps its room (NC2)."""
    words = [
        "Field",
        "terminals",
        "and",
        "the",
        "lamp",
        "circuit",
        "for",
        "the",
        "demo",
        "cabinet",
        "panel",
        "wiring",
    ]
    longest = ""
    for count in range(1, len(words) + 1):
        title = " ".join(words[:count])
        result, _pdf = _build(tmp_path / f"t{count}", "", page_title=title)
        if _page_title_cuts(result):
            break
        longest = title
    assert longest
    kept, _pdf = _build(
        tmp_path / "kept",
        _LEGEND,
        customer="DEMO INDUSTRIES GMBH",
        author="A. Andersson",
        page_title=longest,
    )
    assert _page_title_cuts(kept) == []
