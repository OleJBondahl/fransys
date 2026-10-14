"""The page data of the views that stand in place of the drawing: the matrix and the lens (O7, O8).

Each is `derive`'s rows by table index, with no layout: the page only lists them.
"""

from typing import TYPE_CHECKING, Any

from fransys_model.derive import printed_designation, signal_lens, unit_matrix

if TYPE_CHECKING:
    from ._data import _Tables

Json = dict[str, Any]
_MIN_AXIS = 2  # a matrix of one box shows nothing (O7)


def matrix_data(tables: _Tables) -> Json | None:
    """The unit matrix as page data: axis labels and cells `[row, col, count, [[ix, label]]]`."""
    matrix = unit_matrix(tables.model)
    if len(matrix.axis) < _MIN_AXIS:
        return None
    cells = [
        [
            c.row,
            c.col,
            c.count,
            [[tables.item_ix.get(k), printed_designation(tables.model, k)] for k in c.cables],
        ]
        for c in matrix.cells
    ]
    return {"axis": [box.lines[0] for box in matrix.axis], "cells": cells}


def lens_data(tables: _Tables) -> list[Json]:
    """The Signals lens as page data: per PLC module its channels, items by table index."""
    return [
        {
            "designation": module.designation,
            "item": tables.item_ix.get(module.module),
            "channels": [
                {
                    "number": ch.number,
                    "kind": ch.kind.value,
                    "signal": ch.signal_name,
                    "device": ch.device_designation,
                    "device_item": tables.item_ix.get(ch.device_item),
                }
                for ch in module.channels
            ],
        }
        for module in signal_lens(tables.model)
    ]
