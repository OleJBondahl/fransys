"""Field case: a seal-in circuit, a start button in parallel with the contact K1, then a stop button and the coil in series.
The bug: none on today's engine, whose numbers the hand-back records; the parallel pair draws as one column, no crossings.
Fixed by el-0012 (engine switches SW8 row P7.7), the core-path build draws the circuit in one column with no link marker."""

import itertools
from typing import TYPE_CHECKING

import fransys as fr
from _drawn_facts import wire_nets
from _drawn_pages import drawn_pages
from test_core_path_junctions import _seal_in

from fransys_model.layout import LinkMarker, layout_of

if TYPE_CHECKING:
    from pathlib import Path

type _Point = tuple[int, int]


def _crosses(a: tuple[_Point, _Point], b: tuple[_Point, _Point]) -> bool:
    """Whether a horizontal and a vertical segment cross strictly inside both."""
    if (a[0][1] == a[1][1]) == (b[0][1] == b[1][1]):
        return False
    h, v = (a, b) if a[0][1] == a[1][1] else (b, a)
    return min(h[0][0], h[1][0]) < v[0][0] < max(h[0][0], h[1][0]) and (min(v[0][1], v[1][1]) < h[0][1] < max(v[0][1], v[1][1]))


def crossings(result: fr.BuildResult) -> int:
    """The strict crossings between segments of wires of different nets on one page."""
    nets = {w.id: w.net for _, w in wire_nets(result.model)}
    return sum(
        _crosses(s, t)
        for drawing in drawn_pages(result.model).values()
        for one, two in itertools.combinations(drawing.wires, 2)
        if nets[one.id] != nets[two.id]
        for s in itertools.pairwise(one.points)
        for t in itertools.pairwise(two.points)
    )


def test_a_seal_in_circuit_draws_in_one_column_with_no_crossing(tmp_path: Path) -> None:
    result = fr.build(*_seal_in(tmp_path / "cover.md"))
    assert len(drawn_pages(result.model)) == 1
    assert sum(len(drawing.wires) for drawing in drawn_pages(result.model).values()) > 0
    assert crossings(result) == 0
    assert len(layout_of(result.model, LinkMarker)) == 0
    written = fr.write(result, tmp_path / "out", intermediates=tmp_path / "mid")
    assert [p for p in written if p.suffix == ".pdf"]
