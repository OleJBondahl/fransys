"""Field case: the stubs of cables leaving one unit's box printed over each other.
The bug: every leaving line ran the same length and ended in a stub text, so the stub texts sat in one row, over each other.
Fixed by layout-0256: stubs whose boxes meet stand in a staircase, each one tier further out, so no two boxes meet."""

from itertools import pairwise
from typing import TYPE_CHECKING, Any

import fransys as fr
import pytest
from _cabinet_design import cabinet_design
from _drawn_pages import drawn_pages, markers_in, ref_texts
from _model_build_cover import cabinet_document

from electrical_symbols import G_PER_MODULE, LIBRARY, MARKER_TURN_FACING
from fransys_layout.geometry import Box, overlaps, text_width_g, through
from fransys_layout.geometry.units import Point
from fransys_layout.symbols import text_room_on
from fransys_model.layout import sheet_format_of

_CABLES = 3


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    return fr.build(cabinet_design(_CABLES), cabinet_document("demo-outer"))


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
    meeting = [(a, b) for n, a in enumerate(boxes) for b in boxes[n + 1 :] if overlaps(a, b)]
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
