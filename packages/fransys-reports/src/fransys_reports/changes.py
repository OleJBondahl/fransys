"""Model diff report: a `ListingDiff` as CSV or Markdown."""

from fransys_model.derive import natural_key, revision_text
from fransys_model.derive.baseline import (
    CHANGE_COLUMNS,
    Change,
    ListingDiff,
    change_clause,
    change_identity,
    change_sections,
    interface_text,
    renamed_text,
)

from .csv import _csv


def changes_csv(diff: ListingDiff) -> str:
    """Write a listing diff's change list as CSV.

    Formats ``fransys_model.derive.baseline.diff``'s own `changes`, one row per `Change`,
    columns `CHANGE_COLUMNS` (`section, change, subject, field, before, after`) -- the header
    cell is each column's own name, no relabeling (reports-0001). Pure.

    Args:
        diff: A `ListingDiff` from `fransys_model.derive.baseline.diff`.

    Returns:
        The CSV text. Same `diff`, same bytes.
    """
    return _csv(diff.changes, CHANGE_COLUMNS)


def _bullets(section: str, rows: tuple[Change, ...]) -> list[str]:
    """The bullets of one `(section, subject)` group: a rename bullet, then the real changes."""
    renamed = [f"- {renamed_text(row)}" for row in rows if row.change == "renamed"]
    rest = tuple(row for row in rows if row.change != "renamed")
    return [*renamed, *([_bullet(section, rest)] if rest else [])]


def _bullet(section: str, rows: tuple[Change, ...]) -> str:
    """One Markdown bullet for one `(section, subject)` group of `Change` rows (reports-0004)."""
    identity = change_identity(section, rows[0].parts)
    if len(rows) == 1 and rows[0].field == "" and rows[0].change != "changed":
        change = rows[0].change
        verb = "Added" if change == "added" else "Removed"
        detail = rows[0].detail
        if detail:
            return f"- {verb} {identity}: {detail}."
        return f"- {verb} {identity}."
    ports_added = sorted(
        (row.after for row in rows if row.change == "added" and row.field == "ports"),
        key=natural_key,
    )
    ports_removed = sorted(
        (row.before for row in rows if row.change == "removed" and row.field == "ports"),
        key=natural_key,
    )
    clauses = []
    if ports_added:
        clauses.append("ports added " + ", ".join(ports_added))
    if ports_removed:
        clauses.append("ports removed " + ", ".join(ports_removed))
    clauses.extend(change_clause(row) for row in rows if row.change == "changed")
    return f"- Changed {identity}: {'; '.join(clauses)}."


def changes_markdown(diff: ListingDiff) -> str:
    """Write a listing diff as a Markdown change note.

    A `#` heading, an `Interface X to Y.` line when the interface changed, then one `##`
    section per non-`unit` section with a `Change` row, one bullet per subject; no such
    section gives `No changes.` (reports-0004). Pure.

    Args:
        diff: A `ListingDiff` from `fransys_model.derive.baseline.diff`.

    Returns:
        The Markdown text. Same `diff`, same bytes.
    """
    before = revision_text(diff.a.version, diff.a.revision)
    after = revision_text(diff.b.version, diff.b.revision)
    lines = [f"# {diff.a.name}: changes from {before} to {after}"]
    if diff.a.interface != diff.b.interface:
        lines.extend(["", interface_text(diff.a.interface, diff.b.interface)])
    sections = change_sections(diff)
    if not sections:
        lines.extend(["", "No changes."])
        return "\n".join(lines)
    for part in sections:
        lines.extend(["", f"## {part.section.title()}", ""])
        for rows in part.groups:
            lines.extend(_bullets(part.section, rows))
    return "\n".join(lines)
