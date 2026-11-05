"""Field case: the readability guide names each field the reading gives and each it dropped.
The bug: none; a consumer upgrading from 0.20 hunts for `page_cuts`, a field the row no longer carries.
Fixed by el-0043 (amended by R517): the guide says in its own words what stays, what is removed, and what is a setting."""

from pathlib import Path

_GUIDE = Path(__file__).parents[2] / "packages/fransys/src/fransys/guide/readability.md"


def _text() -> str:
    return _GUIDE.read_text(encoding="utf-8")


def test_the_guide_describes_unit_and_fill_percent() -> None:
    text = _text()
    assert "**`unit`.**" in text
    assert "**`fill_percent`.**" in text


def test_the_guide_says_page_cuts_was_removed_and_text_height_is_a_setting() -> None:
    (note,) = (p for p in _text().split("\n\n") if p.startswith("**Removed.**"))
    assert "`page_cuts`" in note
    assert "fixed heights" in note
