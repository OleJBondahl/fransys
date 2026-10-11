"""Field case: a cable's cores between two coils draw as open runs, not as a loop round each coil.

The engineering shape: two relays on one page and one 4-core cable W1 whose cores run from coil A1
to coil A1 and from coil A2 to coil A2. A coil's A1 pin faces up and its A2 pin faces down. The
cable stands at the top level, or inside a unit: the layout is the same.

The bug: the line's end at each coil has two pin rows (up and down), and the line runs on from the
first row's split to the second's (`line_draw._through_rows`). The search goes round the coil. The
A2 core then leaves downward, turns right, runs up past the coil and turns back left into the
coil's own column above A1, to join the bundle. The page reads as a closed loop with A1 and A2
joined, and the bold bundle runs on below A2's entry with no core there.

Rule: no bundle segment runs past its last core entry; no core's route re-enters its own coil's
column on the coil's far side; the routes of A1 and A2 share no run along the coil's column.
The repro asserts the correct drawing; its fix is decision layout-0172.
"""

import tempfile
from functools import cache
from itertools import pairwise
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import pytest

from fransys_model.layout import HarnessFanOut, HarnessLine, SymbolPlacement, layout_of

_STEP = 8  # the wiring grid: every drawn vertex is a multiple of it
Pt = tuple[int, int]
_WHERE = pytest.mark.parametrize("where", ["top level", "unit"])


class _Open(NamedTuple):
    pass


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cab(u: Any) -> _Open:
    _cores(u, u.device("K1", "DEMO-RLY-2CO-24"), u.device("K2", "DEMO-RLY-2CO-24"))
    return _Open()


def _cores(d: Any, k1: Any, k2: Any) -> None:
    cable = d.cable("W1", "DEMO-CBL-4G1.5", length_m=1)
    cable.core(1, k1.coil["A1"], k2.coil["A1"])
    cable.core(2, k1.coil["A2"], k2.coil["A2"])


@cache
def _built(*, in_unit: bool) -> fr.BuildResult:
    """Built in the tests' bodies, so a build error is a test FAILURE, not a fixture error."""
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    if in_unit:
        d.add(_cab, "U1")
    else:
        _cores(d, d.device("K1", "DEMO-RLY-2CO-24"), d.device("K2", "DEMO-RLY-2CO-24"))
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


def _grid(points: tuple[Pt, ...]) -> list[Pt]:
    """The wiring-grid points a polyline passes, its vertices included."""
    out: list[Pt] = []
    for (x1, y1), (x2, y2) in pairwise(points):
        n = max(abs(x2 - x1), abs(y2 - y1)) // _STEP
        sx, sy = (x2 > x1) - (x2 < x1), (y2 > y1) - (y2 < y1)
        out += [(x1 + sx * _STEP * k, y1 + sy * _STEP * k) for k in range(n + 1)]
    return out or list(points)


class _Drawn(NamedTuple):
    bundle: tuple[Pt, ...]
    legs: dict[int, dict[Any, tuple[Pt, ...]]]  # branch -> conductor -> split, knee, pin
    coils: tuple[tuple[int, int], ...]  # each coil's x and y


def _drawn(*, in_unit: bool) -> _Drawn:
    """The one bundle polyline, each end's legs, and the coils, read from the layout records."""
    model = _built(in_unit=in_unit).model
    (line,) = layout_of(model, HarnessLine).values()
    legs: dict[int, dict[Any, tuple[Pt, ...]]] = {}
    for fan in layout_of(model, HarnessFanOut).values():
        legs[fan.branch] = {
            leg.conductor: tuple((p.x, p.y) for p in leg.points) for leg in fan.legs
        }
    coils = tuple((c.x, c.y) for c in layout_of(model, SymbolPlacement).values())
    return _Drawn(tuple((p.x, p.y) for p in line.points), legs, coils)


def _on(point: Pt, run: tuple[Pt, Pt]) -> bool:
    (x1, y1), (x2, y2) = run
    return min(x1, x2) <= point[0] <= max(x1, x2) and min(y1, y2) <= point[1] <= max(y1, y2)


def _entry(leg: tuple[Pt, ...], bundle: tuple[Pt, ...]) -> Pt:
    """Where a core leaves the bundle: the last leg point of the prefix that lies on it."""
    runs = list(pairwise(bundle))
    entry = leg[0]
    for point in leg:
        if not any(_on(point, run) for run in runs):
            break
        entry = point
    return entry


def _route(drawn: _Drawn, conductor: Any, branch: int) -> list[Pt]:
    """A core's drawn route from its pin at `branch` to its pin at the other end, grid points."""
    other = next(b for b in drawn.legs if b != branch)
    mine, theirs = drawn.legs[branch][conductor], drawn.legs[other][conductor]
    a, b = (_along(drawn.bundle, leg[0]) for leg in (mine, theirs))
    lo, hi = sorted((a, b))
    stretch = [p for p in _grid(drawn.bundle) if lo <= _along(drawn.bundle, p) <= hi]
    return [*_grid(mine), *stretch, *_grid(theirs)]


def _along(bundle: tuple[Pt, ...], point: Pt) -> int:
    """The distance along the bundle at which `point` lies (the first time it passes it)."""
    done = 0
    for run in pairwise(bundle):
        if _on(point, run):
            return done + abs(point[0] - run[0][0]) + abs(point[1] - run[0][1])
        done += abs(run[1][0] - run[0][0]) + abs(run[1][1] - run[0][1])
    return done


def _column_run(route: list[Pt], col: int) -> set[Pt]:
    """The grid points of `route` where it runs along the column `col`, not just crosses it."""
    on = {p for p in route if p[0] == col}
    return {p for p in on if (p[0], p[1] + _STEP) in on or (p[0], p[1] - _STEP) in on}


def _coil_of(drawn: _Drawn, pin: Pt) -> tuple[int, int]:
    (coil,) = (c for c in drawn.coils if c[0] == pin[0])
    return coil


@_WHERE
def test_no_bundle_segment_runs_past_its_last_core_entry(where: str) -> None:
    """Each end of the bundle polyline is where a core leaves it."""
    drawn = _drawn(in_unit=where == "unit")
    entries = {
        _entry(leg, drawn.bundle) for by_core in drawn.legs.values() for leg in by_core.values()
    }
    assert {drawn.bundle[0], drawn.bundle[-1]} <= entries


@_WHERE
def test_no_core_route_re_enters_its_own_coils_column_on_the_far_side(where: str) -> None:
    """A core that leaves its coil at one pin never runs back along the column beyond the other."""
    drawn = _drawn(in_unit=where == "unit")
    for branch, by_core in drawn.legs.items():
        for conductor, leg in by_core.items():
            pin = leg[-1]
            col, mid = _coil_of(drawn, pin)
            run = _column_run(_route(drawn, conductor, branch), col)
            behind = sorted(p for p in run if (p[1] - mid) * (pin[1] - mid) < 0)
            assert not behind, f"core of the pin at {pin} re-enters the column at {behind}"


@_WHERE
def test_a1_and_a2_share_no_run_along_the_coils_column(where: str) -> None:
    """The routes of a coil's two cores share no run along the coil's column.

    A fan's split is one point by design (layout-0172): a shared point is no fault, a shared run is.
    """
    drawn = _drawn(in_unit=where == "unit")
    for branch, by_core in drawn.legs.items():
        in_column = [
            _column_run(_route(drawn, c, branch), _coil_of(drawn, leg[-1])[0])
            for c, leg in by_core.items()
        ]
        assert not set.intersection(*in_column), (
            f"both cores of a coil run along its column at {in_column}"
        )
