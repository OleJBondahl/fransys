"""The reference labels of the page frame's grid, named by the `[frame]` table."""

from fransys_model.kernel import SchemaError
lazy from fransys_model.layout import FrameForm

from .rows_sheet import FrameLabels

__all__ = ["cell_labels", "frame_labels"]

_KIND = "layout.frame_form"


def _name(key: str, setting: str, index: int) -> str:
    """The label of 0-based `index` under `setting`: `letters` A, B, C, `numbers` 1, 2, 3."""
    if setting == "letters":
        return chr(ord("A") + index)
    if setting == "numbers":
        return str(index + 1)
    msg = f'[frame] {key} is "{setting}"; known: "letters", "numbers"'
    raise SchemaError(msg, kind=_KIND)


def _row_name(form: FrameForm, index: int, rows: int) -> str:
    """The label of the canonical top-down row `index` of `rows`, counted per `row_order`."""
    if form.row_order == "bottom_up":
        index = rows - 1 - index
    elif form.row_order != "top_down":
        msg = f'[frame] row_order is "{form.row_order}"; known: "top_down", "bottom_up"'
        raise SchemaError(msg, kind=_KIND)
    return _name("row_labels", form.row_labels, index)


def cell_labels(form: FrameForm, rows: int, column: int, row: str) -> tuple[str, str]:
    """The printed `(column, row)` of the canonical cell `column` (from 1), `row` (a letter)."""
    return (
        _name("column_labels", form.column_labels, column - 1),
        _row_name(form, ord(row) - ord("A"), rows),
    )


def frame_labels(form: FrameForm, columns: int, rows: int) -> FrameLabels:
    """The column labels left to right and the row labels top down for a frame of that many."""
    return FrameLabels(
        columns=tuple(_name("column_labels", form.column_labels, i) for i in range(columns)),
        rows=tuple(_row_name(form, i, rows) for i in range(rows)),
    )
