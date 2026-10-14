"""Field case: a page title says what the page shows; one that cannot fit names the remedy.

The engineering shape: eleven function blocks "Relay and lamp circuit 1" to "... 11", each with
one relay; a terminal strip `-X1` and a lamp `-H1` in no block; `d.layout.page_title(x1, ...)` names
the strip's page.

The bug: the blocks' texts did not fit the title block's cell, so the frame printed the group
labels instead (`=F1 =F2 =F3 ...`), silently, and a page with no block printed no more than the
unit's name. A reader of the printed sheet learned neither what the page shows nor how to change it.

The rule (decisions model-0136 and pdf-0010 amended by PAGES-TITLES): a page's title is the first
of its candidate texts that fits the cell. The candidates come from `d.layout.page_title` hints,
else the blocks' texts, else the designations the page prints, longest first, ending with a short
form "first to last" where shared leading words print once. A title that fits in none of its forms
is cut with "…" and raises `TITLE_BLOCK_TEXT_OVERFLOW`, whose message names `d.layout.page_title`.
"""

import re
from itertools import pairwise
from typing import TYPE_CHECKING

import fransys as fr
import pypdfium2
import pytest

if TYPE_CHECKING:
    from pathlib import Path

_TITLE = re.compile(r"Page title\r\n(.+?)\r\nScope", re.DOTALL)


def _build(root: Path, *, blocks: int, hint: str | None) -> tuple[fr.BuildResult, list[str]]:
    """The cabinet with `blocks` circuits, `-X1` wired to `-H1`; the schematic pages' titles."""
    d = fr.design("demo_parts", place="C1")
    d.project(title="Cabinet", number="CAB-1", customer="Demo Co", revision=1, author="d")
    d.revision(1, date="2026-10-12", text="First issue", created="XX")
    cabinet = d.location("C1", "Cabinet")
    relays = []
    for i in range(1, blocks + 1):
        with d.function(f"F{i}", f"Relay and lamp circuit {i}"):
            relays.append(d.device(f"K{i}", "DEMO-RLY-2CO-24"))
    for a, b in pairwise(relays):
        d.wire(a.coil["A2"], b.coil["A1"], wire=("WH", 0.75))
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    h1 = d.device("H1", "DEMO-LAMP-24")
    d.wire(x1.run("SIG", 1)[1], h1.lamp["1"], wire=("WH", 0.75))
    if hint is not None:
        d.layout.page_title(x1, hint)
    cover = root / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    result = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=cover))
    fr.write(result, out_dir=root / "out", intermediates=root / "inter")
    (pdf,) = (root / "out").glob("*.pdf")
    document = pypdfium2.PdfDocument(pdf)
    texts = [page.get_textpage().get_text_range() for page in document]
    titles = [m.group(1).replace("\r\n", " ") for t in texts if (m := _TITLE.search(t))]
    return result, [t for t in titles if t not in {"Cover", "Sheets", "Terminal list", "BOM"}]


@pytest.fixture(scope="module")
def titled(tmp_path_factory: pytest.TempPathFactory) -> tuple[fr.BuildResult, list[str]]:
    return _build(tmp_path_factory.mktemp("titled"), blocks=11, hint="Field terminals")


@pytest.fixture(scope="module")
def unhinted(tmp_path_factory: pytest.TempPathFactory) -> tuple[fr.BuildResult, list[str]]:
    return _build(tmp_path_factory.mktemp("unhinted"), blocks=0, hint=None)


@pytest.fixture(scope="module")
def too_long(tmp_path_factory: pytest.TempPathFactory) -> tuple[fr.BuildResult, list[str]]:
    return _build(tmp_path_factory.mktemp("long"), blocks=0, hint="Field terminals " * 12)


def test_the_blocks_texts_print_once_first_to_last_not_as_group_labels(titled) -> None:
    _, titles = titled
    assert (
        titles[0] == "Relay and lamp circuit 1 to 6"
    )  # PAGE-PAD (layout-0187): the padded page holds six circuits
    assert not any(re.search(r"=F\d", title) for title in titles)


def test_the_page_that_draws_the_strip_reads_the_hint(titled) -> None:
    _, titles = titled
    assert titles[1] == "Field terminals"


def test_without_the_hint_the_page_reads_its_designations_in_drawn_order(unhinted) -> None:
    _, titles = unhinted
    assert titles == ["-X1, -H1"]


def test_a_title_that_cannot_fit_is_cut_and_names_the_hint_as_the_remedy(too_long) -> None:
    result, titles = too_long
    assert titles[0].endswith("…")
    (found,) = [f for f in fr.check(result) if f.code == "TITLE_BLOCK_TEXT_OVERFLOW"]
    assert "d.layout.page_title" in found.message
