"""Field case: the readability guide names each field the reading gives and each it dropped.

Engineering shape: a consumer upgrading from 0.20 reads `fr.readability(result)` rows and looks
in the guide for `unit`, `fill_percent`, `page_cuts` and `text_height_mm`.

Purpose: `unit` and `fill_percent` are on the row (the guide describes them); `page_cuts` is
removed because a `Drawing` does not carry it, and `text_height_mm` is a setting. The guide says
each in its own words, so no reader hunts a field that is gone. Deciding record: el-0043,
amended by R517.
"""

from pathlib import Path

_GUIDE = Path(__file__).parents[2] / "packages/fransys/src/fransys/guide/readability.md"


def _text() -> str:
    return _GUIDE.read_text(encoding="utf-8")


def test_the_guide_describes_unit_and_fill_percent() -> None:
    text = _text()
    assert "**`unit`.**" in text
    assert "**`fill_percent`.**" in text


def test_the_guide_says_page_cuts_was_removed_and_text_height_mm_is_a_setting() -> None:
    (note,) = (p for p in _text().split("\n\n") if p.startswith("**Removed.**"))
    assert "`page_cuts`" in note
    assert "`text_height_mm`" in note
    assert "[font.heights]" in note
