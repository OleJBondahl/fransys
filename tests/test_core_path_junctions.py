"""A seal-in circuit on the core path draws the junction dots the old engine draws (layout-0335).

The engineering shape: a start button S1 in parallel with the contactor's own contact K1, between
S2 and the coil. Two nets each branch at a contact pin: the old engine draws 2 dots there.
"""

from typing import TYPE_CHECKING, Any

import fransys as fr
from _drawn_pages import drawn_pages

if TYPE_CHECKING:
    from pathlib import Path

OLD_ENGINE_DOTS = 2
MEETING_WIRES = 2  # a dot sits where at least two drawn wires end


def _seal_in(cover: Path) -> tuple[fr.Design, Any]:
    d = fr.design("demo_parts")
    room = d.location("C1", "Cabinet")
    supply = d.terminal_strip("X1", "DEMO-TB-2.5", 2, place="C1")
    s1 = d.device("S1", "DEMO-PB-NO", place="C1")
    s2 = d.device("S2", "DEMO-PB-NO", place="C1")
    k1 = d.device("K1", "DEMO-RLY-2CO-24", place="C1")
    with d.function("SEAL", "Seal-in"):
        d.series(supply[1], s2.sw, s1.sw, k1.coil, supply[2], wire=("BU", 0.75))
        d.detail.wire(s2.sw["B"], k1.co_1["11"], wire=("BU", 0.75))
        d.detail.wire(k1.co_1["14"], k1.coil["A1"], wire=("BU", 0.75))
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, room, cover=cover)


def test_a_seal_in_core_build_has_the_old_engines_junction_count(tmp_path: Path) -> None:
    result = fr.build(*_seal_in(tmp_path / "cover.md"))
    pages = drawn_pages(result.model)
    dots = [(page, s) for page, d in pages.items() for s in d.symbols if s.key == "junction-dot"]
    assert len(dots) == OLD_ENGINE_DOTS
    for page, dot in dots:
        ends = [(w.points[i][0], w.points[i][1]) for w in pages[page].wires for i in (0, -1)]
        assert ends.count((dot.x, dot.y)) >= MEETING_WIRES
    written = fr.write(result, tmp_path / "out", intermediates=tmp_path / "mid")
    assert [p for p in written if p.suffix == ".pdf"]
