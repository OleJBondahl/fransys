"""Reference numbering (`derive.drawing_text`): `row_letter`, `frame_row`,
`position_text`'s new signature, `_reference_group`'s four shapes, and `reference_number`'s
per-drawing-set count.

Hand-built records only, the same conventions as `test_drawing_text.py` (`_ids`, `_key`,
`_sheet`, `add_all`, `freeze`), kept in a file of its own so this work never touches a
file another agent is concurrently editing.
"""

import itertools
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from fransys_model.derive import marker_targets as dt
from fransys_model.kernel import Id
from fransys_model.layout import (
    DrawingSet,
    Page,
    PageRole,
    SheetFormat,
)
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import FunctionKind, PortRole

if TYPE_CHECKING:
    from collections.abc import Callable

PRODUCED_BY = "test-engine 0.0.0"

# The same house-conventions sheet as `test_drawing_text.py`: content_width_mm=400,
# content_height_mm=257, module_mm=2.5 -> 1280 grid units wide (8 columns), 822 tall (6 rows).
CONTENT_WIDTH_GRID = 1280
FRAME_COLUMNS = 8
CONTENT_HEIGHT_GRID = 822
FRAME_ROWS = 6


def _ids() -> Callable[[str], Id[Any]]:
    """A fresh id maker: distinct `kind`s may safely reuse the same numeric value."""
    counter = itertools.count(1)

    def make(kind: str) -> Id[Any]:
        return Id(kind=kind, value=f"{next(counter):032x}")

    return make


def _key(id_: Id[Any], *tail: str) -> tuple[str, ...]:
    return (str(id_.value)[:8], *tail)


def _sheet(new_id: Callable[[str], Id[Any]]) -> SheetFormat:
    id_ = new_id("layout.sheet_format")
    return SheetFormat(
        id=id_,
        key=_key(id_),
        name="test sheet",
        width_mm=420,
        height_mm=297,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=400,
        content_height_mm=257,
        frame_columns=FRAME_COLUMNS,
        frame_rows=FRAME_ROWS,
        module_mm=Decimal("2.5"),
    )


def _drawing_set(
    new_id: Callable[[str], Id[Any]], *, number: int, location: Id[Any] | None = None
) -> DrawingSet:
    id_ = new_id("layout.drawing_set")
    return DrawingSet(
        id=id_, key=_key(id_), location=location, number=number, produced_by=PRODUCED_BY
    )


def _page(
    new_id: Callable[[str], Id[Any]],
    *,
    drawing_set: Id[DrawingSet],
    number: int,
    sheet_format: Id[SheetFormat] | None,
) -> Page:
    id_ = new_id("layout.page")
    return Page(
        id=id_,
        key=_key(id_),
        drawing_set=drawing_set,
        number=number,
        role=PageRole.CONTROL,
        sheet_format=sheet_format,
        groups=(),
        produced_by=PRODUCED_BY,
    )


def _item(new_id: Callable[[str], Id[Any]], *, designation: str) -> Item:
    id_ = new_id("item")
    return Item(
        id=id_,
        key=_key(id_),
        part=None,
        parent=None,
        position=None,
        tag=designation,
        description="an invented item",
    )


def _function(new_id: Callable[[str], Id[Any]], *, item: Id[Item]) -> Function:
    id_ = new_id("function")
    return Function(
        id=id_, key=_key(id_), item=item, template=None, name="fn", kind=FunctionKind.COIL
    )


def _port(new_id: Callable[[str], Id[Any]], *, function: Id[Function]) -> Port:
    id_ = new_id("port")
    return Port(
        id=id_, key=_key(id_), function=function, template=None, name="1", role=PortRole.GENERIC
    )


# --------------------------------------------------------------------------------------
# row_letter
# --------------------------------------------------------------------------------------


# --------------------------------------------------------------------------------------
# frame_row
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
