"""Field case: lines leaving one side of a column nest, so a block diagram needs no crossing.

The engineering shape (column): a hub is cabled to four boxes. Of those, the first box is cabled
to two others in the same column, and both lines leave its east side for boxes lower down.
The shape (ring): twelve boards in a ring, a hub cabled to four of them, and a second cable on
one pair of ring neighbours. A drawing exists in which no two lines cross.

The bug: the farther target did not take the outer end and the outer track, so the spans
interleaved (column: one crossing). In the ring, a same-column line on the outermost track also
stood in the way of a line that enters the same box from the next column (two crossings).
Fixing decision: layout-0201 (same-column ends and tracks nest, and take the tracks nearest the
column).
"""

import tempfile
from functools import cache
from itertools import combinations
from pathlib import Path

import fransys as fr
import pytest

from fransys_model.layout import DiagramLine, layout_of

type Edges = tuple[tuple[str, str], ...]

_COLUMN: Edges = (("H", "A"), ("H", "B"), ("H", "C"), ("H", "D"), ("A", "B"), ("A", "C"))
_RING: Edges = (
    *((f"B{i:02d}", f"B{(i + 1) % 12:02d}") for i in range(12)),
    *(("H", f"B{i:02d}") for i in (0, 1, 2, 4)),
    ("B00", "B01"),
)


@cache
def _built(edges: Edges) -> fr.BuildResult:
    tags = sorted({t for edge in edges for t in edge})
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Nest\n", encoding="utf-8")
        d = fr.design("demo_parts")
        devices = {tag: d.device(tag, "DEMO-CONN-2P") for tag in tags}
        for n, (a, b) in enumerate(edges, start=1):
            d.cable(f"W{n}", "DEMO-CBL-4G1.5", length_m=2).core(1, devices[a][1], devices[b][1])
        return fr.build(d, fr.document(fr.DocumentPreset.SYSTEM, None, cover=cover))


def _crossed(
    p: tuple[int, int], q: tuple[int, int], r: tuple[int, int], s: tuple[int, int]
) -> bool:
    """Whether segments pq and rs cross at a point inside both."""

    def side(a: tuple[int, int], b: tuple[int, int], c: tuple[int, int]) -> int:
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    return side(p, q, r) * side(p, q, s) < 0 and side(r, s, p) * side(r, s, q) < 0


def _crossings(result: fr.BuildResult) -> int:
    runs = [
        [((a.x, a.y), (b.x, b.y)) for a, b in zip(line.points, line.points[1:], strict=False)]
        for line in layout_of(result.model, DiagramLine).values()
    ]
    return sum(
        _crossed(*one, *other)
        for first, second in combinations(runs, 2)
        for one in first
        for other in second
    )


@pytest.mark.parametrize("edges", [_COLUMN, _RING], ids=["column", "ring"])
def test_same_side_lines_draw_with_no_crossing(edges: Edges) -> None:
    result = _built(edges)
    assert len(layout_of(result.model, DiagramLine)) == len(edges)
    assert _crossings(result) == 0
