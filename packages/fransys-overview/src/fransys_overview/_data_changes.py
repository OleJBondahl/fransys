"""The changes layer's data: per view, which boxes and lines a `ListingDiff` marks (O19).

The marks are `derive.diff_marks`' (overview-0011): a subject not drawn on a view marks its
nearest drawn ancestor box, and a removed item marks, as changed, its first drawn earlier
ancestor. This module writes them, and `derive.diff_rest`'s list, as the page's JSON.
"""

from typing import TYPE_CHECKING, Any

from fransys_model.derive import diff_marks, diff_rest, revision_text

if TYPE_CHECKING:
    from fransys_model.derive import DiffViewMarks, ViewRows
    from fransys_model.derive.baseline import ListingDiff

    from ._data import _Tables


def _flat(view: DiffViewMarks, *, on_line: bool) -> list[list[Any]]:
    return [[m.at, m.status] for m in view.marks if m.on_line == on_line]


def changes_data(
    tables: _Tables, drawn: list[ViewRows], diff: ListingDiff | None
) -> dict[str, Any] | None:
    """`{"since", "views": [[boxes, lines]], "rest"}`, or `None` with no diff.

    `boxes` and `lines` hold `[index, "added" | "changed"]` per view of `drawn`. `rest` holds
    `[kind, text]` for each thing no box or line of any view carries: removed ones always.
    """
    if diff is None:
        return None
    views = [diff_marks(tables.model, rows, diff) for rows in drawn]
    return {
        "since": f"{diff.a.name} {revision_text(diff.a.version, diff.a.revision)}",
        "views": [[_flat(v, on_line=False), _flat(v, on_line=True)] for v in views],
        "rest": [[r.status, r.text] for r in diff_rest(diff, views)],
    }


__all__ = ["changes_data"]
