"""Field case: a page title says what the page shows.
The bug: the blocks' texts did not fit the title cell, so the frame printed group labels silently.
Fixed by model-0136 and pdf-0010 (amended by PAGES-TITLES), the first candidate that fits; else cut and TITLE_BLOCK_TEXT_OVERFLOW."""

import re
from itertools import pairwise
from typing import TYPE_CHECKING

import fransys as fr
import pypdfium2
import pytest
from _model_build_cover import unit_document

if TYPE_CHECKING:
    from pathlib import Path

# the drawn title block reads its values in slot-id order: ... number, page title, revision, ...
# pdfium reads a page's glyphs in lines or in columns by their shapes and then drops the word spaces, so the text is compared without whitespace
_TITLE = re.compile(r"CAB-1(.+?)1\.12026-10-12")


def _flat(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _build(root: Path, *, blocks: int) -> tuple[fr.BuildResult, list[str]]:
    """The cabinet with `blocks` circuits, `-X1` wired to `-H1`; the schematic pages' titles."""
    d = fr.design("demo_parts", place="C1")
    d.project(title="Cabinet", number="CAB-1", customer="Demo Co", revision=1, author="d")
    d.revision(1, date="2026-10-12", text="First issue", created="XX")
    cabinet = d.location("C1", "Cabinet")
    relays = []
    for i in range(1, blocks + 1):
        with d.function(f"F{i}", f"Relay and lamp circuit {i}"):
            relays.append(d.device(f"K{i}", "DEMO-RLY-2CO-24"))
    for a, b in pairwise([*relays, *relays[:1]]):
        d.series(a.coil["A2"], b.coil["A1"], wire=("WH", 0.75))
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    h1 = d.device("H1", "DEMO-LAMP-24")
    d.series(x1.run("SIG", 1)[1].inner, h1.lamp["1"], wire=("WH", 0.75))
    d.series(x1[2].inner, h1.lamp["2"], wire=("WH", 0.75))
    result = fr.build(d, unit_document(cabinet))
    fr.write(result, out_dir=root / "out", intermediates=root / "inter")
    (pdf,) = (root / "out").glob("*.pdf")
    document = pypdfium2.PdfDocument(pdf)
    texts = [_flat(page.get_textpage().get_text_range()) for page in document]
    titles = [m.group(1) for t in texts if (m := _TITLE.search(t))]
    return result, [t for t in titles if t not in {"Cover", "Sheets", "Terminallist", "BOM"}]


@pytest.fixture(scope="module")
def titled(tmp_path_factory: pytest.TempPathFactory) -> tuple[fr.BuildResult, list[str]]:
    return _build(tmp_path_factory.mktemp("titled"), blocks=11)


@pytest.fixture(scope="module")
def unhinted(tmp_path_factory: pytest.TempPathFactory) -> tuple[fr.BuildResult, list[str]]:
    return _build(tmp_path_factory.mktemp("unhinted"), blocks=0)


def test_the_blocks_texts_print_once_first_to_last_not_as_group_labels(titled) -> None:
    _, titles = titled
    assert titles[0] == _flat("Relay and lamp circuit 1 to 6")  # PAGE-PAD (layout-0187): the padded page holds six circuits
    assert not any(re.search(r"=F\d", title) for title in titles)


def test_without_blocks_the_page_reads_its_designations_in_drawn_order(unhinted) -> None:
    _, titles = unhinted
    assert titles == [_flat("-X1, -H1")]
