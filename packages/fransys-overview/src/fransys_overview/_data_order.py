"""The reading order of a view's boxes, by position: the panel lists them in this order.

Wrapped row first, then x, then y. A box starts a new row when it begins below the row's greatest
bottom, so a box under another (a strip under a device) or a little apart stays in its row.
"""

from typing import Any
lazy from collections.abc import Sequence


def reading_order(boxes: Sequence[Any]) -> list[int]:
    """The indexes of `boxes` (records with `x`, `y` and `height`) in reading order."""
    rows: list[list[int]] = []
    bottom = 0
    for i in sorted(range(len(boxes)), key=lambda i: (boxes[i].y, boxes[i].x, i)):
        if rows and boxes[i].y < bottom:
            rows[-1].append(i)
            bottom = max(bottom, boxes[i].y + boxes[i].height)
        else:
            rows.append([i])
            bottom = boxes[i].y + boxes[i].height
    return [i for row in rows for i in sorted(row, key=lambda i: (boxes[i].x, boxes[i].y, i))]
