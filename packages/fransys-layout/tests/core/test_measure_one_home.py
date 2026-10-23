"""The recut measures what the solve placed, and names no kind (layout-0374, designer R377)."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path
from typing import Any, cast

import pytest

from fransys_layout.core import Facts, PlacementProblem, Size
from fransys_layout.core import cut_measured as measured_module
from fransys_layout.core.cut_measured import Measured

from .cut_fixtures import elem
from .test_widen_pass import OPTS

widen_module = importlib.import_module("fransys_layout.core.widen")
KINDS = {"Trunk", "Marker", "lowered", "reaches"}
WATCHED = {"measured_of", "cut_measured", "_recut"}


def _names(node: ast.AST) -> list[str]:
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            out.append(n.id)
        elif isinstance(n, ast.Attribute):
            out.append(n.attr)
        elif isinstance(n, ast.arg):
            out.append(n.arg)
    return out


def _bodies() -> list[ast.AST]:
    widen_tree = ast.parse(Path(widen_module.__file__).read_text())
    funcs = [n for n in ast.walk(widen_tree) if isinstance(n, ast.FunctionDef)]
    mine = [f for f in funcs if f.name in WATCHED]
    return [*mine, ast.parse(Path(measured_module.__file__).read_text())]


def test_the_measure_and_the_recut_name_no_kind() -> None:
    assert len(_bodies()) == 3  # measured_of, _recut and the cut_measured module
    assert [n for b in _bodies() for n in _names(b) if n in KINDS] == []


def test_the_recut_stops_on_a_repeated_cut(monkeypatch: pytest.MonkeyPatch) -> None:
    """A page still over whose next round gives the same cut is not cut a third time."""
    same = (object(), object())
    calls: list[int] = []
    monkeypatch.setattr(widen_module, "_attempt", lambda *a: (calls.append(a[3]), same)[1])
    monkeypatch.setattr(widen_module, "_excess", lambda *_: 8)
    monkeypatch.setattr(widen_module, "_short", lambda *_: False)
    monkeypatch.setattr(widen_module, "_spans_of", lambda measured, *_: measured)
    prob = PlacementProblem(Size(100, 4000), (elem("e", 40, 32),), (), facts=Facts())
    widen_module._recut((), cast("Any", None), prob, OPTS, Measured())
    assert len(calls) == 2, calls


def test_the_lanes_stop_where_the_page_would_fall_under_the_tallest_block_that_fits_it() -> None:
    """R460: 822 G of room, a block 780 G high, 8 G lanes: five lanes at most (782 G left)."""
    prob = PlacementProblem(Size(100, 4000), (), (), facts=Facts())
    room = prob.area.h - OPTS.page_headroom
    tall = Measured(heights={"fan": room - 5 * OPTS.wiring_grid, "wider": room + 40})
    assert widen_module._lanes(0, 8 * OPTS.wiring_grid, tall, prob, OPTS) == 5
    assert widen_module._lanes(0, 3 * OPTS.wiring_grid, tall, prob, OPTS) == 3
    assert widen_module._lanes(7, 2 * OPTS.wiring_grid, tall, prob, OPTS) == 7
    assert widen_module._lanes(0, 8 * OPTS.wiring_grid, Measured(), prob, OPTS) == 8


@pytest.mark.rule("PAGE-CUT")
def test_a_fan_whose_span_jumps_at_attempt_zero_keeps_the_page_it_fits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R460, R460a: the page never falls under a block that fits it alone.

    The trigger: a widen gap that grows, plus a fan whose span jumps at attempt 0 (272 G in, 736 G
    fresh, the page 114 G over). The old rule took 15 lanes and left 702 G for the 736 G fan.
    """
    prob = PlacementProblem(Size(100, 822 + OPTS.page_headroom), (), (), facts=Facts())
    room = prob.area.h - OPTS.page_headroom
    assert room == 822
    lanes_used: list[int] = []

    def attempt(*a: Any) -> tuple[object, object]:
        lanes_used.append(a[3])
        return (a[3],), (a[3],)

    monkeypatch.setattr(widen_module, "_attempt", attempt)
    monkeypatch.setattr(widen_module, "_excess", lambda *_: 114)
    monkeypatch.setattr(widen_module, "_short", lambda *_: False)
    monkeypatch.setattr(widen_module, "_spans_of", lambda *_: Measured(heights={"fan": 736}))
    widen_module._recut((), cast("Any", None), prob, OPTS, Measured(heights={"fan": 272}))
    assert max(lanes_used) > 0
    assert room - max(lanes_used) * OPTS.wiring_grid >= 736, lanes_used
