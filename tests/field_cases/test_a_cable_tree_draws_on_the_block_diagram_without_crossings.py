"""Field case: a tree of cables draws on the block diagram with no line crossing.

The engineering shape: seven connector devices joined by six cables in a tree. One device is the
hub of four leaves and one cable on to a seventh device that has a further cable. A tree has a
drawing in which no two lines cross. Read at the top of the system and read inside a unit.

The bug: the diagram drew two crossings. Two lines left the hub's east side for boxes lower in the
column; the one that started lower bent nearer the right column, so its first run crossed the
other's vertical run.
"""

import tempfile
from functools import cache
from itertools import combinations
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import pytest

from fransys_model.layout import DiagramLine, layout_of

_EDGES = (("P7", "P2"), ("P1", "P7"), ("P5", "P1"), ("P3", "P1"), ("P4", "P1"), ("P6", "P1"))
_TAGS = ("P1", "P2", "P3", "P4", "P5", "P6", "P7")


class _Open(NamedTuple):
    pass


def _wire(d: Any) -> None:
    devices = {tag: d.device(tag, "DEMO-CONN-2P") for tag in _TAGS}
    for n, (a, b) in enumerate(_EDGES, start=1):
        d.cable(f"W{n}", "DEMO-CBL-4G1.5", length_m=2).core(1, devices[a][1], devices[b][1])


@fr.unit("tree", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _tree(u: Any) -> _Open:
    _wire(u)
    return _Open()


@cache
def _built(*, in_unit: bool) -> fr.BuildResult:
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Tree\n", encoding="utf-8")
        d = fr.design("demo_parts")
        if in_unit:
            d.add(_tree, "U1")
            doc = fr.document(
                fr.DocumentPreset.CABINET_SCHEMATIC,
                "tree",
                cover=cover,
                add=(fr.PageKind.BLOCK_DIAGRAM,),
            )
        else:
            _wire(d)
            doc = fr.document(fr.DocumentPreset.SYSTEM, None, cover=cover)
        return fr.build(d, doc)


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


@pytest.mark.parametrize("in_unit", [False, True], ids=["system", "unit"])
def test_a_tree_of_cables_draws_with_no_crossing(*, in_unit: bool) -> None:
    result = _built(in_unit=in_unit)
    assert len(layout_of(result.model, DiagramLine)) == len(_EDGES)
    assert _crossings(result) == 0
