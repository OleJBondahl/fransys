"""Field case: no block-diagram line runs through another line's label.

The engineering shape: six connector devices, P1 to P6, joined by eight cables of one core each
(P6-P2, P1-P2, P2-P3, P3-P6, P2-P4, P3-P5, P5-P1, P1-P5). The system block diagram draws a line
per cable with its designation printed above the line's longest horizontal run.

The bug: a label was placed with no clearance test, so a perpendicular run of another cable's
line passed through it. Fixed by decision layout-0199 (LEGACY-B3 L12): the label moves clear of
every line, and `lint/diagram.py` reports DIAGRAM_LABEL_STRUCK should one remain.
"""

import tempfile
from functools import cache
from pathlib import Path

import fransys as fr

from fransys_model.layout import DiagramLine, layout_of

_EDGES = ((6, 2), (1, 2), (2, 3), (3, 6), (2, 4), (3, 5), (5, 1), (1, 5))
_HALF_WIDTH = 8  # a label "-W1" is 15 units wide at the house text: this is a little over half
_HALF_HEIGHT = 4


@cache
def _lines() -> tuple[DiagramLine, ...]:
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Cables\n", encoding="utf-8")
        d = fr.design("demo_parts")
        devices = {n: d.device(f"P{n}", "DEMO-CONN-2P") for n in range(1, 7)}
        for k, (a, b) in enumerate(_EDGES, start=1):
            d.cable(f"W{k}", "DEMO-CBL-4G1.5", length_m=2).core(1, devices[a][1], devices[b][1])
        result = fr.build(d, fr.document(fr.DocumentPreset.SYSTEM, None, cover=cover))
    return tuple(layout_of(result.model, DiagramLine).values())


def _strikes(label: DiagramLine, line: DiagramLine) -> bool:
    left, right = label.text_x - _HALF_WIDTH, label.text_x + _HALF_WIDTH
    top, bottom = label.text_y - _HALF_HEIGHT, label.text_y + _HALF_HEIGHT
    for a, b in zip(line.points, line.points[1:], strict=False):
        if a.x == b.x and left < a.x < right and min(a.y, b.y) < bottom and max(a.y, b.y) > top:
            return True
        if a.y == b.y and top < a.y < bottom and min(a.x, b.x) < right and max(a.x, b.x) > left:
            return True
    return False


def test_no_line_runs_through_a_label() -> None:
    lines = _lines()
    assert len(lines) == len(_EDGES)
    assert [
        (one.cable, other.cable) for one in lines for other in lines if _strikes(one, other)
    ] == []
