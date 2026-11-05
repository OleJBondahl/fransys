"""Field case: a harness line that runs on through a fan-out's split draws no dip.
The bug: the line met the first row's split along that row's facing, then ran sideways, dipping one grid below and back.
Fixed by layout-0154, 0158 and W13-DIP: a joint end whose line runs on is met from behind that run, not from its facing."""

import tempfile
from itertools import pairwise
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages
from fransys.colours import BU


class _Open(NamedTuple):
    pass


@fr.unit("demo-ext", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _ext(u: Any) -> _Open:
    k1 = u.device("K1", "DEMO-RLY-2CO-24")
    k2 = u.device("K2", "DEMO-RLY-2CO-24")
    x90 = u.terminal_strip("X90", None, 3, external=True)
    cable = u.cable("W1", "DEMO-CBL-4G1.5", length_m=2)
    cable.core(1, x90[2].outer, k1.coil["A2"])
    cable.core(2, x90[3].outer, k2.coil["A1"])
    u.series(k1.coil["A1"], k2.coil["A2"], wire=(BU, 0.5))
    return _Open()


def _model() -> Any:
    root = Path(tempfile.mkdtemp())
    (root / "cover.md").write_text("# Cabinet\n", encoding="utf-8")
    d = fr.design("demo_parts")
    d.location("CAB", "Cabinet")
    d.add(_ext, "U1", place="CAB")
    schematic = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-ext", cover=root / "cover.md")
    return fr.build(d, schematic).model


def _dir(one: tuple[int, int], two: tuple[int, int]) -> tuple[int, int]:
    """The unit step from `one` to `two` along their axis."""
    return (two[0] > one[0]) - (two[0] < one[0]), (two[1] > one[1]) - (two[1] < one[1])


def test_a_line_meets_a_fan_split_along_the_row_it_leaves_on() -> None:
    """At the split of a two-row fan the line passes through, its run in and out are one way."""
    model = _model()
    turns, through = [], 0
    for drawing in drawn_pages(model).values():
        lines = [w for w in drawing.wires if w.style == "trunk"]
        # a split is a vertex that is not an end of its line and joins two of its runs
        for line in lines:
            points = list(line.points)
            for (a, b), (_, c) in zip(pairwise(points), pairwise(points[1:]), strict=False):
                if _dir(a, b) != (0, 0) and _dir(b, c) != (0, 0):
                    through += 1
                    if _dir(a, b) != _dir(b, c):
                        turns.append((a, b, c))
    assert through >= 1
    assert turns == []
