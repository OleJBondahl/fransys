"""Which drawn box or line of a view each row of a `ListingDiff` marks (overview-0011, O19).

The diff names the system's own items, units, boundary functions and conductors. The roll-up
of a subject onto a view is `view_rollup`'s. A removed item marks, as changed, the first of its
earlier ancestors drawn on the view (overview-0005).
"""

from typing import Any
lazy from collections.abc import Sequence

lazy from fransys_model.kernel import Id, Model

from .baseline_subjects import change_subjects
from .rows_marks import DiffMark, DiffRest, DiffViewMarks
from .view_rollup import subject_marks, view_lookup
lazy from .rows_baseline import Change, ListingDiff
lazy from .rows_overview_view import ViewRows

__all__ = ["diff_marks", "diff_rest"]

_REMOVED = "removed"
_ADDED = "added"
_CHANGED = "changed"


def _is_gone(change: Change) -> bool:
    return change.change == _REMOVED and change.field == ""


def _kind(change: Change) -> str:
    """A row about one field of a thing that stays, or a removed item's ancestor, is a change."""
    return change.change if change.field == "" and change.change != _REMOVED else _CHANGED


def _candidates(model: Model, diff: ListingDiff) -> list[tuple[int, list[Id[Any]]]]:
    """Per row, the subjects it can mark: its own; a removed item's earlier ancestors."""
    subjects = change_subjects(model, None)
    changes = diff.changes
    found: list[tuple[int, list[Id[Any]]]] = [
        (at, [s])
        for at, c in enumerate(changes)
        if not _is_gone(c) and (s := subjects.get((c.section, c.subject))) is not None
    ]
    for ancestry in sorted(diff.ancestry, key=lambda a: a.change):
        if _is_gone(changes[ancestry.change]):
            ancestors = [s for t in ancestry.ancestors if (s := subjects.get(("items", t)))]
            found.append((ancestry.change, ancestors))
    return found


def _put(marks: dict[int, str], at: int, kind: str) -> None:
    if marks.get(at) != _ADDED:
        marks[at] = kind


def diff_marks(model: Model, rows: ViewRows, diff: ListingDiff) -> DiffViewMarks:
    """The boxes and lines of the view `rows` that `diff` marks, and which rows marked.

    A subject not drawn counts on its nearest drawn ancestor box. A line wins over a box for one
    row; an added mark is never turned into a changed one. Boxes come first, by index.
    """
    lookup = view_lookup(model, rows)
    boxes: dict[int, str] = {}
    lines: dict[int, str] = {}
    shown: set[int] = set()
    for at, candidates in _candidates(model, diff):
        for subject in candidates:
            on_boxes, on_lines = subject_marks(model, rows, lookup, subject)
            for one in on_lines or on_boxes:
                _put(lines if on_lines else boxes, one, _kind(diff.changes[at]))
                shown.add(at)
            if on_lines or on_boxes:
                break
    marks = [DiffMark(on_line=False, at=a, status=k) for a, k in sorted(boxes.items())]
    marks += [DiffMark(on_line=True, at=a, status=k) for a, k in sorted(lines.items())]
    return DiffViewMarks(marks=tuple(marks), shown=tuple(sorted(shown)))


def diff_rest(diff: ListingDiff, views: Sequence[DiffViewMarks]) -> tuple[DiffRest, ...]:
    """The rows no view marked, once per kind and subject: removed, then added, then changed."""
    marked = {at for view in views for at in view.shown}
    rows = [
        (_REMOVED if _is_gone(c) else _kind(c), c.subject)
        for at, c in enumerate(diff.changes)
        if at not in marked
    ]
    order = {_REMOVED: 0, _ADDED: 1, _CHANGED: 2}
    return tuple(
        DiffRest(status=k, text=t)
        for k, t in sorted(dict.fromkeys(rows), key=lambda r: order[r[0]])
    )
