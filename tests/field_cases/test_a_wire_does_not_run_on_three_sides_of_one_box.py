"""Field case: a coil wire ran round three sides of a header's box and read as a second outline.

The engineering shape: a unit with a header `-U1-J7` mated to a loom plug `-P17`, the loom's
other plug `-P18` mated to a contactor's lead housing `-K1-J10`, whose pins join the coil and
the aux contact. The contactor's pins 1, 3 and 4 face wires from the right, so the coil's pin 2
can only reach its housing over the header's stack.

The bug: the coil wire ran along the left, top and right of `-U1-J7`, each within two grid steps
of the box inside the unit's outline, so it drew a thin rectangle round the box. The fix (decision
layout-0176): a route whose path runs along three sides of one box is searched again
with the strip behind the box's closed side blocked, so the wire goes the other way round.

The measure: for each box, the sides a segment of one wire runs along within 16 grid units
outside the side (and over its span); three or more sides is a wrap.
"""

import sys
from dataclasses import replace
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

from fransys_layout.stages import pagerun
from fransys_model import derive
from fransys_model.layout import ConnectorBox, HarnessLine, Route, layout_of

if TYPE_CHECKING:
    import fransys as fr
    import pytest

_TESTS_DIR = Path(__file__).resolve().parent.parent
if str(_TESTS_DIR) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts the tests folder on `sys.path`.
    sys.path.insert(0, str(_TESTS_DIR))

from ha_study_board import build  # noqa: E402 -- needs the tests folder on sys.path first

GAP = 16  # two wiring-grid steps

type Point = tuple[int, int]


class Rect(NamedTuple):
    x: int
    y: int
    width: int
    height: int


def _sides_along(a: Point, b: Point, box: Rect) -> set[str]:
    right, bottom = box.x + box.width, box.y + box.height
    if a[0] == b[0]:
        low, high = sorted((a[1], b[1]))
        if not (low < bottom and box.y < high):
            return set()
        found = {"left": box.x - GAP <= a[0] <= box.x, "right": right <= a[0] <= right + GAP}
    else:
        low, high = sorted((a[0], b[0]))
        if not (low < right and box.x < high):
            return set()
        found = {"top": box.y - GAP <= a[1] <= box.y, "bottom": bottom <= a[1] <= bottom + GAP}
    return {side for side, hit in found.items() if hit}


def _wraps(points: list[Point], box: Rect) -> bool:
    sides: set[str] = set()
    for a, b in pairwise(points):
        sides |= _sides_along(a, b, box)
    return len(sides) >= 3


def _wrapping(result: fr.BuildResult) -> list[tuple[str, str]]:
    model = result.model
    boxes = list(layout_of(model, ConnectorBox).values())
    wires = [*layout_of(model, Route).values(), *layout_of(model, HarnessLine).values()]
    return [
        (type(wire).__name__, derive.connector_box_lines(model, box.function)[0])
        for wire in wires
        for box in boxes
        if box.page == wire.page
        and _wraps([(p.x, p.y) for p in wire.points], Rect(box.x, box.y, box.width, box.height))
    ]


def test_the_measure_sees_a_wire_round_three_sides_of_a_box() -> None:
    box = Rect(10, 10, 20, 20)
    round_it = [(8, 40), (8, 8), (32, 8), (32, 40)]
    assert _wraps(round_it, box)
    assert not _wraps(round_it[:3], box)
    assert not _wraps([(8, 40), (8, 8), (80, 8), (80, 40)], box)


def test_no_wire_runs_along_three_sides_of_one_box() -> None:
    assert _wrapping(build()) == []


def test_a_router_called_with_no_wrap_gap_keeps_the_framing_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = pagerun.PageRoom
    monkeypatch.setattr(pagerun, "PageRoom", lambda **room: replace(real(**room), wrap_gap=None))
    assert _wrapping(build(plc_above=True)) != []
