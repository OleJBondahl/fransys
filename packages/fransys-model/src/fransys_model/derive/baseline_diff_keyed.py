"""Rename detection for a keyed diff (CR2, model-0300): pair rows by key, rename `a` to `b`."""

from dataclasses import replace

from .baseline_codec_keys import has_item_keys
from .order import NaturalKey, natural_key
from .rows_baseline import BaselineBoundary, BaselineItem, Change, Listing


def keyed_pair(a: Listing, b: Listing) -> bool:
    """True when both listings carry item keys, so the diff follows an item across a rename."""
    return has_item_keys(a) and has_item_keys(b)


def _rename_row(section: str, old: str, new: str) -> Change:
    return Change(
        section=section,
        change="renamed",
        subject=new,
        field="",
        before=old,
        after=new,
        parts=(old, new),
        detail="",
    )


def _renames(
    a_rows: tuple[BaselineItem, ...] | tuple[BaselineBoundary, ...],
    b_rows: tuple[BaselineItem, ...] | tuple[BaselineBoundary, ...],
    a_subject: str,
    b_subject: str,
) -> dict[str, str]:
    """Old designation to new, for each row whose key (and pin) is on both sides, text moved."""
    b_by_key = {(r.key, getattr(r, "pin", None)): r for r in b_rows}
    found: dict[str, str] = {}
    for row in a_rows:
        other = b_by_key.get((row.key, getattr(row, "pin", None)))
        if other is not None and other.designation != row.designation:
            found[row.designation or a_subject] = other.designation or b_subject
    return found


def rename_to_b(
    a: Listing, b: Listing, a_subject: str, b_subject: str
) -> tuple[Listing, list[Change]]:
    """`a` with each renamed item and boundary designation set to `b`'s, and the `renamed` rows."""
    items = _renames(a.items, b.items, a_subject, b_subject)
    boundary = _renames(a.boundary, b.boundary, a_subject, b_subject)
    rows = [_rename_row("items", old, new) for old, new in items.items()]
    rows += [_rename_row("boundary", old, new) for old, new in boundary.items()]
    moved = tuple(
        replace(
            r,
            designation=items.get(r.designation or a_subject, r.designation),
        )
        for r in a.items
    )
    kept = tuple(
        replace(r, designation=boundary.get(r.designation or a_subject, r.designation))
        for r in a.boundary
    )
    return replace(a, items=moved, boundary=kept), rows


def renamed_first(change: Change) -> tuple[bool, NaturalKey, str]:
    """The sort key of an items or boundary row: `renamed` rows first, then subject, then field."""
    return (change.change != "renamed", natural_key(change.subject), change.field)
