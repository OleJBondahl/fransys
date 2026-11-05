"""layout-0406: the marker rule on top of `stretched_body`: the axis choice, one home for el."""

import pytest

from electrical_symbols import LIBRARY, MARKER_TURNED, marker_symbol
from fransys_layout.symbols import library_symbol, marker_rule, stretched_body

pytestmark = pytest.mark.rule("PAGE-FRAME")

_FLAG = library_symbol(LIBRARY, marker_symbol("tag"))
_TURNED = library_symbol(LIBRARY, MARKER_TURNED)


def test_across_the_wire_the_width_stretches_along_x() -> None:
    stretch, body = marker_rule(_FLAG, "R0", (83, 40), LIBRARY, along=False)
    assert stretch == (("x", 83), ("y", 40))
    assert body == stretched_body(_FLAG, "R0", {"x": 83, "y": 40}, LIBRARY)


def test_along_the_wire_the_height_stretches_along_y() -> None:
    stretch, body = marker_rule(_TURNED, "R180", (12, 75), LIBRARY, along=True)
    assert stretch == (("y", 75), ("x", 12))
    assert (body.w, body.h) == (12, 75)


def test_each_axis_reads_its_own_length() -> None:
    assert marker_rule(_FLAG, "R0", (83, 20), LIBRARY, along=False) != marker_rule(_FLAG, "R0", (90, 20), LIBRARY, along=False)
    assert marker_rule(_FLAG, "R0", (83, 24), LIBRARY, along=False) != marker_rule(_FLAG, "R0", (83, 20), LIBRARY, along=False)
