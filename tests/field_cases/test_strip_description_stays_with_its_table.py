"""Field case: a terminal strip's description never stands alone at a column foot.

The engineering shape: a long strip, then a second strip with a multi-line description and a
short table, so the second strip's heading falls at or near the foot of the left column.

The bug: the description paragraph sat between the heading and the table, so it could end the
left column while its table began the right one. The rule (L7, decision pdf-0026): a table's
heading, its description, its header row and its first data row never split across a column foot.
"""

lazy from pathlib import Path

import fransys as fr
import pypdfium2
import pytest

_DESCRIPTION = "ZZDESC " + "long words " * 12


def _pdf(root: Path, filler: int) -> Path:
    """The terminal list of a `filler`-terminal strip and a described three-terminal strip."""
    d = fr.design("demo_parts")
    d.project(title="Cabinet", number="CAB-1", customer="Demo Co", revision=1, author="d")
    d.revision(1, date="2026-10-12", text="First issue", created="XX")
    cabinet = d.location("C1", "Cabinet")
    d.terminal_strip("X1", "DEMO-TB-2.5", filler, place="C1")
    d.terminal_strip("X2", "DEMO-TB-2.5", 3, place="C1", description=_DESCRIPTION)
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


def _place(pdf: Path, key: str) -> tuple[int, bool]:
    """`(page, in the right column)` of the first `key` on a terminal list page."""
    document = pypdfium2.PdfDocument(pdf)
    try:
        for number, page in enumerate(document):
            text = page.get_textpage()
            found = text.get_text_range().find(key)
            if "Terminal list" in text.get_text_range() and found >= 0:
                return number, text.get_charbox(found)[0] > page.get_size()[0] / 2
        raise AssertionError(key)
    finally:
        document.close()


@pytest.mark.parametrize("filler", [36, 37, 38])
def test_the_description_stands_in_its_tables_column(tmp_path: Path, filler: int) -> None:
    """The description and the first data row share a page and a column at the left foot."""
    pdf = _pdf(tmp_path, filler)
    assert _place(pdf, "ZZDESC") == _place(pdf, "-X2:1 1")
