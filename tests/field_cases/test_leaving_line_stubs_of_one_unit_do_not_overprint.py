"""Field case: the stubs of cables leaving one unit's box printed over each other.
The bug: every leaving line ran the same length and ended in a stub text, so the stub texts sat in one row, over each other.
Fixed by layout-0256: stubs whose boxes meet stand in a staircase, each one tier further out, so no two boxes meet."""

from itertools import pairwise
from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
import pytest
from _drawn_pages import drawn_pages, markers_in, ref_texts
from _model_build_cover import cabinet_document

from electrical_symbols import LIBRARY, MARKER_TURN_FACING
from fransys_layout.geometry import G_PER_MODULE, Box, boxes_meet, text_width_g, through
from fransys_layout.geometry.units import Point
from fransys_layout.symbols import text_room_on
from fransys_model.layout import sheet_format_of

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
    d.layout.profile(hide_unused_pins=True)
    relays = [d.device(f"K{k}", "DEMO-RLY-4CO-24", interface=("co_1",)) for k in (1, 3, 5)]
    f8 = d.device("F8", "DEMO-MCB-2P", interface=("pole_1",))
    xf = d.terminal_strip("XF", "DEMO-TB-2.5", 6, interface=(4, 5, 6), bridged=True)
    d.series(f8.pole_1["1"], xf[1], wire=("BK", 1.5))
    return _Cabinet(
        f8,
        relays[0],
        relays[1],
        relays[2],
        d.device("DI", "DEMO-PLC-DI-16", interface=("di_9", "di_11", "di_13")),
        xf,
    )


@fr.unit("demo-outer", revision=1, interface_version=1, date="2026-01-01", text="r", by="XX")
def _outer(d: fr.Design) -> _Top:
    d.layout.profile(hide_unused_pins=True)
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


def _box(marker: DrawnSymbol, text_height: int) -> Box:
    """The box as drawn: one module out of the port along its facing, as wide as its longest text."""
    width = max(text_width_g(text, height=text_height) for text in ref_texts(marker))
    out = marker.y - G_PER_MODULE - text_height if marker.orient == MARKER_TURN_FACING["N"] else marker.y + G_PER_MODULE
    return Box(x=marker.x - width // 2, y=out, width=width, height=text_height)


def _stubs(built: fr.BuildResult) -> list[tuple[Any, Box]]:
    """Each leaving-line stub as `(page, box)`; the case's stubs face north or south.

    The Drawing marks no stub as a leaving line's: the three cables leave toward the one device DI.
    """
    height = text_room_on(built.model, sheet_format_of(built.model, None), LIBRARY)
    return [
        (page, _box(m, height))
        for page, drawing in drawn_pages(built.model).items()
        for m in markers_in(drawing)
        if ref_texts(m)[0].endswith("-CSC-DI")
    ]


def test_the_case_has_three_stubs_in_one_row(built: fr.BuildResult) -> None:
    pages = {page for page, _ in _stubs(built)}
    assert len(_stubs(built)) == _CABLES
    assert len(pages) == 1


def test_no_two_stub_boxes_meet(built: fr.BuildResult) -> None:
    boxes = [box for _, box in _stubs(built)]
    assert len(boxes) == _CABLES, "the check would pass over nothing"
    meeting = [(a, b) for n, a in enumerate(boxes) for b in boxes[n + 1 :] if boxes_meet(a, b, closed=False)]
    assert meeting == []


def test_no_line_runs_through_a_stub_box(built: fr.BuildResult) -> None:
    stubs = _stubs(built)
    assert len(stubs) == _CABLES, "the check would pass over nothing"
    hits = [
        (page, box)
        for page, drawing in drawn_pages(built.model).items()
        for line in drawing.wires
        if line.style != "wire"
        for stub_page, box in stubs
        if stub_page == page
        for a, b in pairwise(line.points)
        if through((Point(x=a[0], y=a[1]), Point(x=b[0], y=b[1])), box)
    ]
    assert hits == []


if TYPE_CHECKING:
    from fransys_layout.drawing import DrawnSymbol
