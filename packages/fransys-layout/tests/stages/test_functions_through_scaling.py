"""`functions_through` tests only what sits in the cells its stub spans, whatever the page holds.

The south marker at (0, 0) has the stub (0, 0) to (0, 40): one run over 6 wiring-grid cells
(y 0 to 40 in steps of 8, x 0). The page has the marker's own body, two foreign bodies the stub
crosses, and `far` bodies a thousand units away, two ports each. The exact tests are counted on
`crosses` and `_on`. Each is at most `cells * 3`: no cell of this page holds more than three
entries of one kind. Adding bodies far away leaves both counts equal.
"""

from samples import hid
lazy import pytest

from fransys_layout.geometry import Box, Point
from fransys_layout.stages import LinkMarker, MarkerSide
from fransys_layout.stages import stub_runs as module
from fransys_layout.stages.stub_runs import functions_through, solids, stub_runs

_OWN = hid("function", 1)
_MARKER = LinkMarker(
    connection=hid("connection", 1),
    port=hid("port", 1),
    side=MarkerSide.OWNER,
    drawing_set=1,
    page=1,
    at=Point(x=0, y=0),
    box=Box(x=-12, y=40, width=24, height=8),
    partner_page=2,
)
_CELLS, _PER_CELL = 6, 3


def _page(far: int) -> tuple[dict, dict]:
    """The own body, two crossed bodies, and `far` far bodies with two ports each."""
    bodies = {
        _OWN: Box(x=-5, y=-10, width=10, height=10),
        hid("function", 2): Box(x=-5, y=10, width=10, height=10),
        hid("function", 3): Box(x=-5, y=24, width=10, height=8),
    }
    ports = {_OWN: (Point(x=0, y=0),)}
    for number in range(far):
        x = 1000 + 40 * number
        handle = hid("function", 10 + number)
        bodies[handle] = Box(x=x, y=0, width=16, height=16)
        ports[handle] = (Point(x=x, y=0), Point(x=x + 16, y=16))
    return bodies, ports


def _counts(far: int, monkeypatch: pytest.MonkeyPatch) -> tuple[int, int, tuple]:
    """The body tests, the port tests and the result of one `functions_through` call."""
    count = {"crosses": 0, "on": 0}

    def counted(name: str):
        original = getattr(module, name)

        def wrapper(*args):
            count[name.strip("_")] += 1
            return original(*args)

        monkeypatch.setattr(module, name, wrapper)

    counted("crosses")
    counted("_on")
    found = functions_through(_MARKER, solids(*_page(far)))
    return count["crosses"], count["on"], found


def test_the_exact_tests_stay_within_the_cells_of_the_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    """UNDO: `CellIndex.meeting` returns every item, and 23 body tests pass the bound of 18."""
    crossed, on, found = _counts(20, monkeypatch)
    assert found == (hid("function", 2), hid("function", 3))
    assert crossed <= _CELLS * _PER_CELL
    assert on <= _CELLS * _PER_CELL


def test_far_bodies_added_to_the_page_add_no_exact_test(monkeypatch: pytest.MonkeyPatch) -> None:
    """UNDO: `CellIndex.meeting` returns every item, and doubling the far bodies doubles them."""
    assert _counts(20, monkeypatch)[:2] == _counts(40, monkeypatch)[:2]


def test_the_stub_is_one_run_over_the_cells_the_bound_counts() -> None:
    """The bound's cell count is read off the stub: one run, y 0 to 40, six cells of 8."""
    (run,) = stub_runs(_MARKER)
    assert (run.x, run.y, run.to_x, run.to_y) == (0, 0, 0, 40)
