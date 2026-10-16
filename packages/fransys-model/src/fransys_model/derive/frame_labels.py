"""The reference labels of the page frame's grid."""

from .frame_position import row_letter
from .rows_sheet import FrameLabels

__all__ = ["frame_labels"]


def frame_labels(columns: int, rows: int) -> FrameLabels:
    """Column numbers `1..columns` and row letters `A..` for a frame of that many of each."""
    return FrameLabels(
        columns=tuple(str(i + 1) for i in range(columns)),
        rows=tuple(row_letter(i) for i in range(rows)),
    )
