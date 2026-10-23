"""XF-HINTS part 3 (R467 C6): a unit profile's `group_ranks` order the schematic's function groups.

Three relay blocks built in a unit that ranks them F3, F2, F1 stand in that order on the page. The
overview already read the ranks; the drawing path did not (guide `drawing.md`, order hints).
"""

from typing import NamedTuple
lazy from pathlib import Path

import fransys as fr
from fransys.colours import BU

from fransys_model.layout import Page, layout_of


class _Cabinet(NamedTuple):
    pass


def _groups_in_page_order(tmp_path: Path, *, ranked: bool) -> list[str]:
    names: dict[object, str] = {}

    @fr.unit(
        "cab",
        revision=1,
        interface_version=1,
        date="2026-01-01",
        text="First",
        by="XX",
        title="Cabinet",
        number="C-1",
    )
    def cabinet(c: fr.Design) -> _Cabinet:
        for i in (1, 2, 3):
            with c.function(f"F{i}", f"Relay {i}") as group:
                k = c.device(f"K{i}", "DEMO-RLY-2CO-24")
                feed = c.terminal_strip(f"X{i}", "DEMO-TB-2.5", 2)
                c.series(feed, k.coil, feed, wire=(BU, 0.75))
            names[group.id] = f"F{i}"
        if ranked:
            c.layout.profile(group_ranks={"F3": 1, "F2": 2, "F1": 3})
        return _Cabinet()

    cover = tmp_path / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    d = fr.design("demo_parts")
    d.add(cabinet, "U1")
    result = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "cab", cover=cover))
    pages = sorted(layout_of(result.model, Page).values(), key=lambda p: (p.drawing_set, p.number))
    return [names[g.group] for p in pages for g in p.groups]


def test_the_ranks_of_the_profile_order_the_groups(tmp_path: Path) -> None:
    assert _groups_in_page_order(tmp_path, ranked=True) == ["F3", "F2", "F1"]


def test_without_ranks_the_groups_stand_in_natural_order(tmp_path: Path) -> None:
    assert _groups_in_page_order(tmp_path, ranked=False) == ["F1", "F2", "F3"]
