"""A core page with no group is titled by its designations, as today's engine titles it (FIX3 5).

The lamps page (two coils, one wire) printed "-K1, -K2" before the core path and a blank title
after it: the core writes its designations as drawn texts, not labels. A page with a group keeps
the group's text ("Card", model-0097).
The built model also holds the old engine's pages; only the core pages (with drawn symbols) count.
"""

import sys
import tempfile
from pathlib import Path

import fransys as fr
from fransys.colours import BU

from fransys_model.derive import page_title
from fransys_model.kernel import evolve
from fransys_model.layout import Membership, Page, layout_of

sys.path.append(str(Path(__file__).parents[3] / "tests"))
from _card_case import card_case_drafts
from _drawn_pages import drawn_pages


def _written(drafts):
    return fr.build(*drafts).model


def _titles(drafts) -> list[str]:
    written = _written(drafts)
    core = set(drawn_pages(written))
    return [
        page_title(written, page) for page in layout_of(written, Page).values() if page.id in core
    ]


def _lamps() -> tuple:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    first, second = d.device("K1", "DEMO-RLY-2CO-24"), d.device("K2", "DEMO-RLY-2CO-24")
    d.detail.wire(first.coil["A2"], second.coil["A1"], wire=(BU, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)


def test_the_lamps_page_is_titled_by_its_two_designations() -> None:
    assert _titles(_lamps()) == ["-K1, -K2"]


def test_a_page_with_a_group_keeps_the_groups_text() -> None:
    assert "Card" in _titles(card_case_drafts(16))


def test_the_title_reads_the_membership_rows_not_the_drawings() -> None:
    """Can fail: the membership rows go, and the designations go."""
    written = _written(_lamps())
    stripped = evolve(written, remove=list(layout_of(written, Membership)))
    titles = [page_title(stripped, page) for page in layout_of(stripped, Page).values()]
    assert "-K1, -K2" not in titles
