"""Field case: a harness line that runs on through a fan-out's split draws no dip.

The engineering shape: a cabinet unit holds two relays `K1` and `K2`, a part-less strip `X90`
supplied by others, and a 4-core cable `W1` whose two cores leave `X90:2` and `X90:3` for the two
coils. The cable's end at `X90` holds pins in two rows, so its line runs through the first row's
split on to the second row's.

The bug: the line was routed to the first row's split arriving along that row's facing, then run
on sideways, so it dipped one grid below the split row and came back up to it: down, across, up,
on. Nothing in the path turned back, so the unspike pass left it.

Rule (layout-0154, 0158): a line through a fan's split meets it along the row it runs on.
Fixed by W13-DIP: a joint end whose line runs on is met from behind that run, not from its facing.
"""

import tempfile
from itertools import pairwise
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages


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
    return _Open()


def _model() -> Any:
    root = Path(tempfile.mkdtemp())
    (root / "cover.md").write_text("# Cabinet\n", encoding="utf-8")
    d = fr.design("demo_parts")
    d.location("CAB", "Cabinet")
    d.add(_ext, "U1", place="CAB")
    schematic = fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC, "demo-ext", cover=root / "cover.md"
    )
    return fr.build(d, schematic).model


def _dir(one: tuple[int, int], two: tuple[int, int]) -> tuple[int, int]:
    """The unit step from `one` to `two` along their axis."""
    return (two[0] > one[0]) - (two[0] < one[0]), (two[1] > one[1]) - (two[1] < one[1])


def test_a_line_meets_a_fan_split_along_the_row_it_leaves_on() -> None:
    """At the split of a two-row fan the line passes through, its run in and out are one way."""
    model = _model()
    turns, through = [], 0
    for drawing in drawn_pages(model).values():
        lines = [w for w in drawing.wires if w.lanes > 1]
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
