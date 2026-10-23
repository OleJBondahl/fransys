"""Field case: a seal-in circuit draws in one column with no crossing and no reference.

The engineering shape: a start button S1 stands in parallel with the contactor's own auxiliary
contact K1, between the same two nets, then a stop button S2 and the coil K1 in series, fed from
and returned to a supply strip. The contact and the button are two paths between the same two
nets: a cross-link of the circuit that is a loop, not a tree.

The bug: none on today's engine, whose numbers the hand-back records. The core path holds the
same shape: the parallel pair is two lanes of one column joined by horizontals, so the circuit is
one column on one page, with 0 crossings and 0 references (SW8 row P7.7, design section 4.10).

The rule: engine switches SW8 row P7.7, decision el-0012. The case runs through `fr.build` on the
core path: the build draws the page Drawings, and this circuit needs no marker
record, so the case holds. The built result also writes a PDF (lift round, P7.1 B on main).
"""

import itertools
from typing import TYPE_CHECKING, Any

import fransys as fr
from _drawn_pages import drawn_pages

from fransys_model.layout import LinkMarker, layout_of

if TYPE_CHECKING:
    from pathlib import Path

type _Point = tuple[int, int]


def _gap(model, fact: str):
    """A fact the page Drawing lacks (strict xfail, GAP-FLIP-DRAWING-SUBJECT)."""
    msg = f"GAP-FLIP-DRAWING-SUBJECT: no {fact} for {model.digest}"
    raise AssertionError(msg)


def cross_links_case_drafts(cover: Path) -> tuple[fr.Design, Any]:
    """The design and its schematic document: S2 in series with S1 parallel to K1's own contact."""
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


def _crosses(a: tuple[_Point, _Point], b: tuple[_Point, _Point]) -> bool:
    """Whether a horizontal and a vertical segment cross strictly inside both."""
    if (a[0][1] == a[1][1]) == (b[0][1] == b[1][1]):
        return False
    h, v = (a, b) if a[0][1] == a[1][1] else (b, a)
    return min(h[0][0], h[1][0]) < v[0][0] < max(h[0][0], h[1][0]) and (
        min(v[0][1], v[1][1]) < h[0][1] < max(v[0][1], v[1][1])
    )


def crossings(result: fr.BuildResult) -> int:
    """The strict crossings between segments of wires of different nets on one page."""
    nets = _gap(result.model, "wire net")
    return sum(
        _crosses(s, t)
        for drawing in drawn_pages(result.model).values()
        for one, two in itertools.combinations(drawing.wires, 2)
        if nets[one.id] != nets[two.id]
        for s in itertools.pairwise(one.points)
        for t in itertools.pairwise(two.points)
    )


def test_a_seal_in_circuit_draws_in_one_column_with_no_crossing(tmp_path: Path) -> None:
    result = fr.build(*cross_links_case_drafts(tmp_path / "cover.md"))
    assert len(drawn_pages(result.model)) == 1
    assert sum(len(drawing.wires) for drawing in drawn_pages(result.model).values()) > 0
    assert crossings(result) == 0
    assert len(layout_of(result.model, LinkMarker)) == 0
    written = fr.write(result, tmp_path / "out", intermediates=tmp_path / "mid")
    assert [p for p in written if p.suffix == ".pdf"]
