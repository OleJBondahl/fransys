"""Field case: sixteen push buttons in series to a 16-channel input card cross no wire.

The engineering shape: a 24 V supply feeds sixteen normally closed buttons, each in series to the
next free channel of one digital input module.

The bug: today's engine put the buttons in one row in the order the tags gave them while the
module's channels printed in their own order, so the wires from the buttons to the card crossed
each other (84 crossings in the study's build).

The rule (decision el-0011, spec SWITCHES SW8 row P7.6): on the core path the card's pins spread
to the pitch of the columns hung under them, so no wire crosses. (A supply's own box does not
hold its pins yet: that rule is parked as BOX-PIN-ATTACH.) The solve-level counts are in
`packages/fransys-el/tests/test_input_cards.py`.
"""

from collections import Counter
from itertools import combinations, pairwise
from typing import TYPE_CHECKING, Any

import fransys as fr
from _page_drawings import page_drawings
from fransys.colours import BU

from fransys_model.layout import PowerSymbol, layout_of

if TYPE_CHECKING:
    from pathlib import Path

BUTTONS = 16


def input_card_case_drafts(cover: Path) -> tuple[fr.Design, Any]:
    """The design and cabinet document of the sixteen series buttons and the one card."""
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"), names=("P24", "P0"))
    card = d.device("A1", "DEMO-PLC-DI-16")
    for n in range(1, BUTTONS + 1):
        button = d.device(f"S{n}", "DEMO-PB-NC")
        button.sw.plc(fr.DI, f"Button {n}")
        d.series(dc.plus, button.sw, card, wire=(BU, 0.75))
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=cover)


def _segments(points: tuple) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    return list(pairwise(points))


def _cross(a: tuple, b: tuple) -> bool:
    """Whether a horizontal and a vertical segment meet strictly inside both."""
    (ax0, ay0), (ax1, ay1) = a
    (bx0, by0), (bx1, by1) = b
    if ay0 == ay1 and bx0 == bx1:
        return min(ax0, ax1) < bx0 < max(ax0, ax1) and min(by0, by1) < ay0 < max(by0, by1)
    if ax0 == ax1 and by0 == by1:
        return _cross(b, a)
    return False


def crossings(result: fr.BuildResult) -> int:
    """The wire-over-wire crossings of the core path's drawings, page by page."""
    total = 0
    for drawing in page_drawings(result).values():
        wires = [_segments(w.points) for w in drawing.wires]
        total += sum(_cross(s, t) for one, two in combinations(wires, 2) for s in one for t in two)
    return total


def drawn_wires(result: fr.BuildResult) -> int:
    """The wires the core path drew, all pages."""
    return sum(len(drawing.wires) for drawing in page_drawings(result).values())


def test_sixteen_series_buttons_to_a_card_cross_no_wire(tmp_path: Path) -> None:
    d, document = input_card_case_drafts(tmp_path / "cover.md")
    result = fr.build(d, document)
    assert crossings(result) == 0
    leads = len(layout_of(result.model, PowerSymbol))  # one lead per power symbol (el-0045)
    assert drawn_wires(result) == BUTTONS + leads, "one wire per button, one lead per power symbol"
    left_out = [f.message for f in result.findings if f.code == "NET_NOT_DRAWN"]
    assert all("port -G1:" in m for m in left_out), left_out
    # 24 V bar at the supply pin and the 16 feed pins, ground at the return (el-0020)
    assert Counter(p.symbol for p in layout_of(result.model, PowerSymbol).values()) == {
        "power-supply": BUTTONS + 1,
        "ground": 1,
    }
