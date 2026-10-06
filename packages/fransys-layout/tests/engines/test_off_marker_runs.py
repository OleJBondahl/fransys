"""R1 (layout deep dive, designer's ruling): an off-stub box sits over the columns it names,
and every stub ends on it. A row of one cable's stubs is cut where another column stands
between two ends, and a shared box is at least as wide as its run of stubs.

Can-fail, checked by hand: without `_runs` the first test sees one box over all three ends;
without the run width the second test's box is narrower than its two stubs apart.
"""

from samples import PROFILE, SHEET, built, connection, drawn, hid, placed, standing

from fransys_layout.stages.references.off_stubs import _cuts, _off_markers, _runs
from fransys_layout.stages.references.types import MarkerScene, OffStubs
from fransys_layout.stages.types import StubText


def _markers(at: dict[int, tuple[int, str]]):
    """Functions placed at `(x, column)`; each of 1..3 has a W1 core leaving its `14` port."""
    ends = [n for n in at if n < 4]  # function 4 is a foreign column
    scene = MarkerScene(
        tuple(placed(n, x=x, y=160, name=column) for n, (x, column) in at.items()),
        tuple(drawn(n) for n in at),
        SHEET,
        PROFILE,
    )
    off = OffStubs(
        tuple(connection(n, n, 90 + n) for n in ends),
        off_texts={
            hid("port", n * 10 + 2): [StubText(cable="-W1", far="+DB-X0", port=f":{n}")]
            for n in ends
        },
    )
    return built(scene, _off_markers(scene, standing(scene, off)))


def test_a_column_between_two_ends_cuts_the_row_into_two_boxes() -> None:
    markers = _markers({1: (64, "a"), 2: (96, "a"), 4: (240, "b"), 3: (400, "c")})
    texts = {m.port: m.text for m in markers}
    assert texts[hid("port", 12)] == texts[hid("port", 22)] == "-W1 → +DB-X0:1 2"
    assert texts[hid("port", 32)] == "-W1 → +DB-X0:3"


def test_a_shared_box_spans_its_run_of_stubs() -> None:
    markers = _markers({1: (64, "a"), 2: (320, "a")})
    (box,) = {m.box for m in markers}
    assert box.x < 64
    assert box.x + box.width > 320


def _end(column: int, x: int):
    return ((column, x), hid("conn", x), None, ":", None)


def test_a_stranger_pin_between_two_ends_of_one_column_cuts_the_run() -> None:
    """M8: `_cuts` keeps a stranger's `(column, x)`; without it the two ends share one run."""
    ends = [_end(0, 10), _end(0, 50)]
    cuts = _cuts(ends, 1, [(0, 30)])
    assert cuts == [(0, 30)]
    assert [len(run) for run in _runs(ends, cuts)] == [1, 1]
    assert [len(run) for run in _runs(ends, _cuts(ends, 1, []))] == [2]


def test_a_column_without_an_end_cuts_the_run_between_its_neighbours() -> None:
    """R1: `_cuts` names each column no end stands in; without it the two ends share one run."""
    ends = [_end(0, 10), _end(2, 10)]
    cuts = _cuts(ends, 3, [])
    assert cuts == [(1,)]
    assert [len(run) for run in _runs(ends, cuts)] == [1, 1]
