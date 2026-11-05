"""Reference numbering (`derive.drawing_text`): `row_letter`,
`position_text`'s new signature, `_reference_group`'s four shapes, and `reference_number`'s
per-drawing-set count.
"""

from typing import TYPE_CHECKING, Any

from derive_helpers import (
    record_key as _key,
)

from fransys_model.derive import marker_targets as dt
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import FunctionKind, PortBoundary
lazy from fransys_model.kernel import Id

if TYPE_CHECKING:
    from collections.abc import Callable

PRODUCED_BY = "test-engine 0.0.0"

# The same house-conventions sheet as `test_drawing_text.py`: content_width_mm=400,
# content_height_mm=257, module_mm=2.5 -> 1280 grid units wide (8 columns), 822 tall (6 rows).
CONTENT_WIDTH_GRID = 1280
FRAME_COLUMNS = 8
CONTENT_HEIGHT_GRID = 822
FRAME_ROWS = 6


def _function(new_id: Callable[[str], Id[Any]], *, item: Id[Item]) -> Function:
    id_ = new_id("function")
    return Function(id=id_, key=_key(id_), item=item, template=None, name="fn", kind=FunctionKind.COIL)


def _port(new_id: Callable[[str], Id[Any]], *, function: Id[Function]) -> Port:
    id_ = new_id("port")
    return Port(id=id_, key=_key(id_), function=function, template=None, name="1", boundary=PortBoundary.GENERIC)


# --------------------------------------------------------------------------------------
# row_letter
# --------------------------------------------------------------------------------------


# --------------------------------------------------------------------------------------
# row_letter
# --------------------------------------------------------------------------------------


# --------------------------------------------------------------------------------------
# position_text
# --------------------------------------------------------------------------------------


# --------------------------------------------------------------------------------------
# _reference_group: the four persisted shapes, plus the pure-stub exclusion
# --------------------------------------------------------------------------------------


# --------------------------------------------------------------------------------------
# reference_number: reading order and the per-drawing-set restart
# --------------------------------------------------------------------------------------


def test_two_ends_in_one_cell_print_one_line() -> None:
    """The full branch (model-0139) drops a repeated position, as the count branch does."""
    assert dt.target_lines(1, ["1A", "1A"]) == ["#1-1A"]
    assert dt.target_lines(1, ["1A", "1A", "1A"]) == ["#1-1A"]
    assert dt.target_lines(1, ["1A", "2A", "2A"]) == ["#1-1A +1"]
