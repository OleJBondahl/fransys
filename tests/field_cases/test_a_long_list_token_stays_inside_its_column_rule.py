"""Field case: a cabinet whose strip and devices have long hyphenated tags, so a terminal row's long names are long tokens in the terminal list.
The bug (v0.15): a column gets no width beside auto columns, so its text and its header run past the table's right rule.
Fixed by pdf-0027, no glyph crosses a column rule or the frame, a long token breaks only at a hyphen or slash, and a header cell wraps."""

from typing import Any
lazy from pathlib import Path

import fransys as fr
import pypdfium2
from fransys.colours import BU
from pypdfium2 import raw

_FOOT = 0.14  # the title block's share of the page height, from the bottom
_SIDE = 30  # the frame's side letters and top numbers, in points
_FRAME = 12.8  # the frame's right edge, from the page's right, in points
_TOP = 20  # a table's top rule lies below this margin; the frame's top ticks do not
_EPS = 0.3  # a glyph box may touch a rule by this much
_STRIP = "X-STRIP-LONG-NAME-FEEDBACK-VALVES-OPEN-LIMIT-SWITCH"
_DEVICE = "KVALVE-FEEDBACK-OPEN-LIMIT-SWITCH-EXTRA-LONG-TOKEN"

Box = tuple[float, float, float, float]


def _pdf(root: Path) -> Path:
    """The cabinet's PDF: three wires between long-tagged devices and a strip; the document prints the terminal list."""
    d = fr.design("demo_parts")
    d.project(title="Cabinet", number="CAB-1", customer="Demo Co", revision=1, author="d")
    d.revision(1, date="2026-10-12", text="First issue", created="XX")
    cabinet = d.location("C1", "Cabinet")
    strip = d.terminal_strip(_STRIP, "DEMO-TB-2.5", 6, place="C1")
    for number in range(1, 4):
        relay = d.device(f"{_DEVICE}-{number}", "DEMO-RLY-2CO-24", place="C1")
        d.series(relay["A1"], strip[number].outer, wire=(BU, 0.5))
        d.series(relay["A2"], strip[number + 3].outer, wire=(BU, 0.5))
    cover = root / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    document = fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC,
        cabinet,
        cover=cover,
    )
    fr.write(fr.build(d, document), out_dir=root / "out", intermediates=root / "inter")
    (pdf,) = (root / "out").glob("*.pdf")
    return pdf


def _in_body(box: Box, width: float, height: float) -> bool:
    left, bottom, _right, top = box
    return _SIDE < left < width - _FRAME and _FOOT * height < bottom and top < height - _SIDE


def _list_page(pdf: Path) -> tuple[Any, list[Any], list[Any]]:
    """The terminal list page: its width, its body glyphs `(box, char)` and its vertical rules."""
    document = pypdfium2.PdfDocument(pdf)
    try:
        for page in document:
            text = page.get_textpage()
            if "Terminal list" not in text.get_text_range():
                continue
            width, height = page.get_size()
            glyphs = [
                (box, char)
                for i in range(text.count_chars())
                if (char := text.get_text_range(i, 1)).strip() and _in_body(box := text.get_charbox(i), width, height)
            ]
            rules = [
                bounds
                for obj in page.get_objects()
                if obj.type == raw.FPDF_PAGEOBJ_PATH
                and (bounds := obj.get_bounds())[2] - bounds[0] < 2
                and bounds[3] - bounds[1] > 5
                and _SIDE < bounds[0] < width - _SIDE
                and _FOOT * height < bounds[1]
                and bounds[3] < height - _TOP
            ]
            return width, glyphs, rules
    finally:
        document.close()
    msg = "no terminal list page"
    raise AssertionError(msg)


def _stray(glyphs: list[tuple[Box, str]], rules: list[Box], width: float) -> list[str]:
    """The glyphs that touch a column rule, or lie past the table's right rule or the frame."""
    table_right = max(rule[2] for rule in rules)
    found = []
    for (left, bottom, right, top), char in glyphs:
        crosses = any(
            left < r_right - _EPS and right > r_left + _EPS and bottom < r_top and top > r_bottom for r_left, r_bottom, r_right, r_top in rules
        )
        if crosses or right > table_right + _EPS or right > width - _FRAME + _EPS:
            found.append(char)
    return found


def test_a_long_label_stays_inside_the_table_and_its_rules(tmp_path: Path) -> None:
    """No glyph of the list lies past the table's right rule or on a column rule."""
    width, glyphs, rules = _list_page(_pdf(tmp_path))
    assert rules
    assert "LIMIT-SWITCH" in "".join(char for _, char in glyphs)
    assert "".join(_stray(glyphs, rules, width)) == ""


def test_the_last_header_wraps_inside_its_cell(tmp_path: Path) -> None:
    """The last column's header ends at or before the table's right rule."""
    pdf = _pdf(tmp_path)
    width, glyphs, rules = _list_page(pdf)
    table_right = max(rule[2] for rule in rules)
    header = [box for box, _ in glyphs if box[1] > max(r[3] for r in rules) - 20]
    assert header
    assert max(box[2] for box in header) <= table_right + _EPS
    assert max(box[2] for box in header) <= width - _FRAME
