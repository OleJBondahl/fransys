"""The label-free corridor of a straight vertical connection: hand-made values only."""

from typing import override
lazy from collections.abc import Iterator

from samples import connection, drawn, hid, placed

from fransys_layout.geometry import Box
from fransys_layout.stages.labels import _corridors, decided_runs
from fransys_layout.stages.stacking import JoinedEnd, JoinedRun
lazy from fransys_layout.stages.types import DrawnFunction

# Function n's `out` port sits 16 below its origin and its `in` port 16 above it (the through
# symbol), both on the origin's x. Function 1 at (104, 96) has its `out` at (104, 112).
_DRAWN = (drawn(1), drawn(2))


def _join(*ports: int, page: int = 1) -> JoinedRun:
    """A joined run over the `out` ports of functions `ports`, in column order."""
    ends = tuple(JoinedEnd(column=("invented", "a"), port=hid("port", n * 10 + 2)) for n in ports)
    return JoinedRun(drawing_set=1, page=page, ends=ends)


def test_a_joined_run_keeps_its_line_between_neighbouring_ends_free() -> None:
    """A join of three ends has two runs, each 2 wide on the ports' y, half a grid short of each
    port; no join, or a bent one, adds nothing (the caller passes only its page's joins)."""
    # UNDO: stages/labels.py:decided_runs, `right - left - 2 * half` -> `right - left`
    #     (the box then runs into both ports)
    row = (
        placed(1, x=40, y=96),
        placed(2, x=200, y=96, name="b"),
        placed(3, x=360, y=96, name="c"),
    )
    three = (drawn(1), drawn(2), drawn(3))
    found = decided_runs(row, three, (), (_join(1, 2, 3),))
    assert found == (
        Box(x=44, y=111, width=152, height=2),
        Box(x=204, y=111, width=152, height=2),
    )
    assert decided_runs(row, three, (), ()) == ()
    bent = (placed(1, x=40, y=96), placed(2, x=200, y=120, name="b"))
    assert decided_runs(bent, three, (), (_join(1, 2),)) == ()


def test_decided_runs_hold_the_corridors_and_the_joined_runs() -> None:
    """One call gives both kinds, corridors first."""
    at = (placed(1, x=104, y=96), placed(2, x=104, y=400, name="b"))
    both = decided_runs(at, _DRAWN, (connection(1, 1, 2),), (_join(1, 2),))
    assert both == _corridors(at, _DRAWN, (connection(1, 1, 2),))


class _Counting(tuple):  # noqa: SLOT001 -- a tuple subclass counts its own passes, no slots needed
    passes = 0

    @override
    def __iter__(self) -> Iterator[DrawnFunction]:
        type(self).passes += 1
        return super().__iter__()
