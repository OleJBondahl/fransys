"""Field case: short groups of one unit stack onto few pages, none of them near empty.

The shape: one cabinet holds fourteen function groups, each two lamps across the 24 V supply. Every
group is far shorter than a page, so the pages are filled by stacking whole groups, split evenly.

The bug: none reported. SWITCHES SW8 (row P7.5) asks that the core path draws the family on no
more pages than today's engine does (four schematic pages for this case; "stacking at 18 pages or
fewer" over the study instances). Passes since ELECTRICAL-MARKERS lets the core path draw.

Decision: el-0010 (short groups on the core path).
"""

from typing import TYPE_CHECKING

import fransys as fr
from fransys.colours import BU
lazy from fransys_author import Location

from fransys_model.layout import Page, layout_of

if TYPE_CHECKING:
    from pathlib import Path

GROUPS = 14
LAMPS = 2
TODAYS_SCHEMATIC_PAGES = 4  # today's engine on this case, measured 2026-10-18


def short_groups_case_drafts() -> tuple[fr.Design, Location]:
    """The design: `GROUPS` function groups of `LAMPS` demo lamps each across one terminal pair."""
    d = fr.design("demo_parts", place="R")
    room = d.location("R", "Room")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
    for g in range(1, GROUPS + 1):
        with d.function(f"F{g}", f"Group {g}"):
            for k in range(1, LAMPS + 1):
                d.series(x1[1], d.device(f"H{g}_{k}", "DEMO-LAMP-24"), x1[2], wire=(BU, 0.75))
    return d, room


def schematic_pages(result: fr.BuildResult) -> int:
    """The pages that draw groups (a cover or an index draws none)."""
    return sum(1 for p in layout_of(result.model, Page).values() if p.groups)


def test_fourteen_short_groups_stack_onto_no_more_pages_than_today(tmp_path: Path) -> None:
    d, room = short_groups_case_drafts()
    (tmp_path / "r.md").write_text("# Room\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    result = fr.build(d, fr.document(preset, room, cover=tmp_path / "r.md"))
    assert schematic_pages(result) <= TODAYS_SCHEMATIC_PAGES
