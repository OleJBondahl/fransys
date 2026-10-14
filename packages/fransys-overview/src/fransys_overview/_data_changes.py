"""The changes layer's data: per view, which boxes and lines a `ListingDiff` marks (O19).

The diff is the system listing's, so it names the system's own items, units, boundary functions
and conductors. A subject not drawn on a view marks its nearest drawn ancestor box, through the
findings layer's roll-up (`_boxes_of`). A removed item marks, as changed, the first of its
earlier ancestors (`ListingDiff.ancestry`) drawn on a view. Any other removed row is listed in
`rest`, and so is an added or changed subject with no box or line on any view.
"""

from typing import TYPE_CHECKING, Any

from fransys_model.derive import revision_text
from fransys_model.derive.baseline import change_subjects

from ._data_findings import _boxes_of, _lookup, _wires_of

if TYPE_CHECKING:
    from fransys_model.derive import ViewRows
    from fransys_model.derive.baseline import Change, ListingDiff

    from ._data import _Tables

_REMOVED = "removed"
_ADDED = "added"
_CHANGED = "changed"


def _kind(change: Change) -> str:
    """A row about one field of a thing that stays, or a removed item's ancestor, is a change."""
    return change.change if change.field == "" and change.change != _REMOVED else _CHANGED


def _mark(marks: dict[int, str], at: int, kind: str) -> None:
    if marks.get(at) != _ADDED:
        marks[at] = kind


def _flat(marks: dict[int, str]) -> list[list[Any]]:
    return [[at, kind] for at, kind in sorted(marks.items())]


def _view_marks(
    tables: _Tables, rows: ViewRows, found: list[tuple[Change, list[Any]]]
) -> tuple[dict[int, str], dict[int, str], set[int]]:
    """The box and line marks of one view, and which of `found` (by index) marked something."""
    lookup = _lookup(tables, rows)
    boxes: dict[int, str] = {}
    lines: dict[int, str] = {}
    shown: set[int] = set()
    for n, (change, candidates) in enumerate(found):
        for subject in candidates:
            ends = _boxes_of(tables, rows, lookup, subject)
            wires = _wires_of(rows, subject, ends)
            for at in wires or dict.fromkeys(ends):
                _mark(lines if wires else boxes, at, _kind(change))
                shown.add(n)
            if wires or ends:
                break
    return boxes, lines, shown


def _rest(
    gone: list[Change], kept: list[Change], shown: set[int], found: list[tuple[Change, list[Any]]]
) -> list[Any]:
    """`[kind, subject text]` per kind in order removed, added, changed; once per subject."""
    marked = {id(found[n][0]) for n in shown}
    off = [c for c in kept if id(c) not in marked]
    rows = [(_REMOVED, c.subject) for c in gone if id(c) not in marked]
    rows += [(_kind(c), c.subject) for c in off]
    order = {_REMOVED: 0, _ADDED: 1, _CHANGED: 2}
    return [list(r) for r in sorted(dict.fromkeys(rows), key=lambda r: order[r[0]])]


def changes_data(
    tables: _Tables, drawn: list[ViewRows], diff: ListingDiff | None
) -> dict[str, Any] | None:
    """`{"since", "views": [[boxes, lines]], "rest"}`, or `None` with no diff.

    `boxes` and `lines` hold `[index, "added" | "changed"]` per view of `drawn`. `rest` holds
    `[kind, text]` for each thing no box or line of any view carries: removed ones always.
    """
    if diff is None:
        return None
    subjects = change_subjects(tables.model, None)
    gone = [c for c in diff.changes if c.change == "removed" and c.field == ""]
    kept = [c for c in diff.changes if c not in gone]
    found = [(c, [s]) for c in kept if (s := subjects.get((c.section, c.subject))) is not None]
    texts = {a.change: a.ancestors for a in diff.ancestry}
    for at, change in enumerate(diff.changes):
        if change in gone and at in texts:
            found.append((change, [s for t in texts[at] if (s := subjects.get(("items", t)))]))
    per_view = [_view_marks(tables, rows, found) for rows in drawn]
    shown = set().union(*(v[2] for v in per_view))
    return {
        "since": f"{diff.a.name} {revision_text(diff.a.version, diff.a.revision)}",
        "views": [[_flat(boxes), _flat(lines)] for boxes, lines, _ in per_view],
        "rest": _rest(gone, kept, shown, found),
    }


__all__ = ["changes_data"]
