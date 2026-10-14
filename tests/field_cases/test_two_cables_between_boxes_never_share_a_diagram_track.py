"""Field case: no two cables' block-diagram lines share a stretch of one track.

The engineering shape: five connector devices, P1 to P5, joined by six cables of one core each
(P4-P1, P2-P3, P2-P1, P5-P4, P2-P4, P1-P4); P4 and P1 are joined by two cables. The system block
diagram draws a line per cable through the channels between its columns.

The bug: two lines of different cables ran along the same coordinate over a stretch, so the
drawing showed one line where there were two. Fixed by decision layout-0199 (LEGACY-B3 L12):
the lines take separate tracks, and `lint/diagram.py` reports DIAGRAM_LINES_SHARE_TRACK should
two still share one.
"""

import tempfile
from functools import cache
from itertools import combinations
from pathlib import Path

import fransys as fr

from fransys_model.layout import DiagramLine, layout_of

_EDGES = ((4, 1), (2, 3), (2, 1), (5, 4), (2, 4), (1, 4))


@cache
def _lines() -> tuple[DiagramLine, ...]:
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Cables\n", encoding="utf-8")
        d = fr.design("demo_parts")
        devices = {n: d.device(f"P{n}", "DEMO-CONN-2P") for n in range(1, 6)}
        for k, (a, b) in enumerate(_EDGES, start=1):
            d.cable(f"W{k}", "DEMO-CBL-4G1.5", length_m=2).core(1, devices[a][1], devices[b][1])
        result = fr.build(d, fr.document(fr.DocumentPreset.SYSTEM, None, cover=cover))
    return tuple(layout_of(result.model, DiagramLine).values())


def _runs(line: DiagramLine) -> list[tuple[int, int, int, int]]:
    """Each run as `(x, y, to_x, to_y)` with its ends ordered."""
    return [
        (min(a.x, b.x), min(a.y, b.y), max(a.x, b.x), max(a.y, b.y))
        for a, b in zip(line.points, line.points[1:], strict=False)
    ]


def _shared(one: tuple[int, int, int, int], other: tuple[int, int, int, int]) -> bool:
    if one[0] == one[2] and other[0] == other[2]:
        return one[0] == other[0] and min(one[3], other[3]) > max(one[1], other[1])
    if one[1] == one[3] and other[1] == other[3]:
        return one[1] == other[1] and min(one[2], other[2]) > max(one[0], other[0])
    return False


def test_no_two_cables_share_a_track() -> None:
    lines = _lines()
    assert len(lines) == len(_EDGES)
    shared = [
        (one.cable, other.cable)
        for one, other in combinations(lines, 2)
        if one.cable != other.cable and any(_shared(r, s) for r in _runs(one) for s in _runs(other))
    ]
    assert shared == []
