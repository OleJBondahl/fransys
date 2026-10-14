"""Field case: the stubs of cables leaving one unit's box printed over each other.

The engineering shape: a cabinet unit inside an outer unit, documented as a cabinet schematic. Three
cables of four cores leave the cabinet's box side by side, each core landing on a different
kind of interface pin (a breaker pole, a relay contact, an input channel, a strip terminal).

The bug: every leaving line runs the same fixed length out of the box and ends in a stub text of
about 250 grid units. The lines stand 4 to 8 grids apart, so the three stub texts sat in one row,
one over the other, and the page read as one smear. `fr.check` gave TEXT_OVERLAP and
WIRE_OVER_LABEL.

The rule (decision layout-0256): stubs whose boxes meet stand in a staircase. Each stub after the
first runs one tier further out and its box starts at its own line, so no two boxes meet and no
line runs through another's box.
"""

from itertools import pairwise
from typing import Any, NamedTuple

import fransys as fr
import pytest
from _model_build_cover import cabinet_document

from fransys_layout.geometry import G_PER_MODULE, Box, boxes_meet, through
from fransys_layout.geometry.units import Point
from fransys_model.layout import HarnessLine, LinkMarker, Side, layout_of

_CABLES = 3
_VALVE = (("coil", "A1"), ("coil", "A2"), ("co_1", "11"), ("co_1", "14"))


class _Cabinet(NamedTuple):
    F8: Any
    K1: Any
    K3: Any
    K5: Any
    DI: Any
    XF: Any


class _Top(NamedTuple):
    T: Any


@fr.unit("demo-inner", revision=1, interface_version=1, date="2026-01-01", text="r", by="XX")
def _inner(d: fr.Design) -> _Cabinet:
    d.layout.profile(hide_unused_pins=True, column_gap=4, row_spacing=400)
    relays = [d.device(f"K{k}", "DEMO-RLY-4CO-24", interface=("co_1",)) for k in (1, 3, 5)]
    return _Cabinet(
        d.device("F8", "DEMO-MCB-2P", interface=("pole_1",)),
        relays[0],
        relays[1],
        relays[2],
        d.device("DI", "DEMO-PLC-DI-16", interface=("di_9", "di_11", "di_13")),
        d.terminal_strip("XF", "DEMO-TB-2.5", 6, interface=(4, 5, 6), bridged=True),
    )


@fr.unit("demo-outer", revision=1, interface_version=1, date="2026-01-01", text="r", by="XX")
def _outer(d: fr.Design) -> _Top:
    d.layout.profile(hide_unused_pins=True, column_gap=16, row_spacing=400)
    cab = d.add(_inner, "CSC")
    for n in range(_CABLES):
        pins = (
            cab.F8.pole_1["2"],
            getattr(cab, f"K{2 * n + 1}").co_1["14"],
            getattr(cab.DI, f"di_{9 + 2 * n}")[str(9 + 2 * n)],
            cab.XF[4 + n],
        )
        with d.function(f"CV{n + 1}", f"Valve {n + 1}"):
            valve = d.device(f"M{n + 1}", "DEMO-RLY-4CO-24")
            cable = d.cable(f"W{n + 1:04d}", "DEMO-CBL-4G1.5")
            for core, (pin, (name, port)) in enumerate(zip(pins, _VALVE, strict=True), start=1):
                cable.core(core, pin, getattr(valve, name)[port])
    return _Top(d.device("T", "DEMO-RLY-4CO-24"))


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_outer, "U1")
    return fr.build(d, cabinet_document("demo-outer"))


def _box(marker: LinkMarker) -> Box:
    """The box as drawn: one module out of the port along `facing`, `box_x` when it was slid."""
    out = (
        marker.y - G_PER_MODULE - marker.height
        if marker.facing is Side.N
        else marker.y + G_PER_MODULE
    )
    x = marker.x - marker.width // 2 if marker.box_x is None else marker.box_x
    return Box(x=x, y=out, width=marker.width, height=marker.height)


def _stubs(built: fr.BuildResult) -> list[tuple[Any, Box]]:
    """Each leaving-line stub as `(page, box)`; the case's stubs face north or south."""
    return [
        (m.page, _box(m))
        for m in layout_of(built.model, LinkMarker).values()
        if m.carrier is not None
    ]


def test_the_case_has_three_stubs_in_one_row(built: fr.BuildResult) -> None:
    pages = {page for page, _ in _stubs(built)}
    assert len(_stubs(built)) == _CABLES
    assert len(pages) == 1


def test_no_two_stub_boxes_meet(built: fr.BuildResult) -> None:
    boxes = [box for _, box in _stubs(built)]
    meeting = [
        (a, b)
        for n, a in enumerate(boxes)
        for b in boxes[n + 1 :]
        if boxes_meet(a, b, closed=False)
    ]
    assert meeting == []


def test_no_line_runs_through_a_stub_box(built: fr.BuildResult) -> None:
    stubs = _stubs(built)
    hits = [
        (line.page, box)
        for line in layout_of(built.model, HarnessLine).values()
        for page, box in stubs
        if page == line.page
        for a, b in pairwise(line.points)
        if through((Point(x=a.x, y=a.y), Point(x=b.x, y=b.y)), box)
    ]
    assert hits == []
