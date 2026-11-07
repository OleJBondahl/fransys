"""Field case: a Parallel of a lamp, a coil and a valve (differing heights), a parallel with a series branch beside it, and circuits in one row.
The bug (checked, not seen): the shorter parts of a Parallel or row could hang from another top than the tallest, a stagger.
Decided by ALIGN-PARALLEL: the parts of one Parallel share a top (held by the row graph in place_y)."""

from types import SimpleNamespace
from typing import TYPE_CHECKING

import fransys as fr
import pytest
from _drawn_facts import pin_turns, symbol_subjects
from fransys.colours import BU

if TYPE_CHECKING:
    from pathlib import Path

_W = (BU, 0.75)


def _lone_parts(d: fr.Design, p: SimpleNamespace) -> None:
    d.series(p.dc.plus, d.parallel(p.h[0], p.k.coil, p.y.coil), p.dc.minus, wire=_W)


def _branch_beside(d: fr.Design, p: SimpleNamespace) -> None:
    d.series(p.dc.plus, d.parallel(p.h[0], p.s[0].sw), p.dc.minus, wire=_W)
    d.series(p.s[0].sw, p.h[1], p.h[2], p.dc.minus, wire=_W)


def _after_a_button(d: fr.Design, p: SimpleNamespace) -> None:
    d.series(p.dc.plus, p.s[2].sw, d.parallel(p.h[0], p.s[0].sw), p.dc.minus, wire=_W)
    d.series(p.s[0].sw, p.h[1], p.h[2], p.h[3], p.dc.minus, wire=_W)


def _circuits_in_a_row(d: fr.Design, p: SimpleNamespace) -> None:
    d.series(p.dc.plus, p.s[0].sw, p.h[0], p.dc.minus, wire=_W)
    d.series(p.dc.plus, d.parallel(p.h[1], p.y.coil), p.dc.minus, wire=_W)
    d.series(p.dc.plus, p.s[1].sw, p.h[2], p.h[3], p.k.coil, p.dc.minus, wire=_W)


# shape: (drawer, tags of the parts that must share one top pin line)
SHAPES = {
    "three-lone-parts": (_lone_parts, ("H1", "K1", "Y1")),
    "branch-beside": (_branch_beside, ("H1", "S1")),
    "after-a-button": (_after_a_button, ("H1", "S1")),
    "circuits-in-a-row": (_circuits_in_a_row, ("S1", "H2", "Y1", "S2")),
}


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_the_parts_of_a_parallel_share_one_top(shape: str, tmp_path: Path) -> None:
    draw, tags = SHAPES[shape]
    d = fr.design("demo_parts", place="C1")
    cab = d.location("C1", "Cabinet")
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"), names=("P24", "P0"))
    lamps = [d.device(f"H{i}", "DEMO-LAMP-24") for i in range(1, 5)]
    buttons = [d.device(f"S{i}", "DEMO-PB-NC") for i in range(1, 4)]
    draw(d, SimpleNamespace(dc=dc, h=lamps, s=buttons, k=d.device("K1", "DEMO-CTR-3P-24"), y=d.device("Y1", "DEMO-VALVE-24")))
    (tmp_path / "cover.md").write_text("# Cabinet\n", encoding="utf-8")
    result = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=tmp_path / "cover.md"))
    tops = {}
    for cell in symbol_subjects(result.model):
        if cell.tag in tags:
            tops[cell.tag] = cell.y + min(p.dy for p in pin_turns(cell.key, orient=cell.orient))
    assert set(tops) == set(tags)
    assert len(set(tops.values())) == 1, tops
