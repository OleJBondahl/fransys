"""The cause of a stale container (WORKFLOW-BLOCKS W8): which direct children moved release.

Read off the `units` rows of the change list `derive.baseline.diff` already gives; no second walk.
"""

from typing import TYPE_CHECKING

from fransys_model.derive import baseline

if TYPE_CHECKING:
    from fransys_model.derive.baseline import Change, Listing


def _child_text(row: Change) -> str | None:
    """`name before → after`, `name added` or `name removed` for one `units` row, else `None`."""
    name = row.parts[1]
    if row.change in ("added", "removed"):
        return f"{name} {row.change}"
    if row.field in ("revision", "version"):
        return f"{name} {row.before} → {row.after}"
    return None


def moved_children(stored: Listing, fresh: Listing) -> str:
    """The direct children whose release moved, each once, joined with `, `; `""` when none."""
    rows = baseline.diff(stored, fresh).changes
    texts = (_child_text(row) for row in rows if row.section == "units")
    return ", ".join(dict.fromkeys(text for text in texts if text is not None))


def sections_text(stored: Listing, fresh: Listing) -> str:
    """The differing sections, with the moved children in parentheses right after `units`."""
    cause = moved_children(stored, fresh)
    sections = baseline.differing_sections(stored, fresh)
    return ", ".join(f"{s} ({cause})" if s == "units" and cause else s for s in sections)
