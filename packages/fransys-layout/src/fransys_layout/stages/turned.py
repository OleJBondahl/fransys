"""A drawn function in a flipped cell: its symbol turned, a boxed view's width kept."""

import dataclasses
from typing import TYPE_CHECKING

from fransys_layout.geometry import Orientation, hull, symbol_geometry

if TYPE_CHECKING:
    from .types import Cell, DrawnFunction


def _turned_function(function: DrawnFunction, cell: Cell) -> DrawnFunction:
    """`function`, its symbol turned when `cell` is a flipped one (`references.joins` reads it)."""
    if not cell.flip or function.geometry.generic_box:
        return function
    # The side element's other port on top. A turned directed pole
    # is mirrored as well (MR180), so top and bottom swap and its poles, markings
    # and tag keep their left-to-right places; every other flip is R180
    flipped = symbol_geometry(
        function.geometry.key,
        poles=function.geometry.poles,
        orientation=Orientation.MR180 if cell.mirror else Orientation.R180,
    )
    if function.boxed:  # layout-0233: a boxed view still holds its box's width once turned
        body = hull([flipped.body, function.geometry.body])
        flipped = dataclasses.replace(flipped, body=body, keepout=hull([flipped.keepout, body]))
    return dataclasses.replace(function, geometry=flipped)
