"""Model diff report: a `ListingDiff` as CSV or Markdown."""

from fransys_model.derive import natural_key, revision_text
from fransys_model.derive.baseline import CHANGE_COLUMNS, Change, ListingDiff, change_identity

from .csv import _csv

# Fixed `##` section order (the diff's own order, minus `unit`, which never
# becomes a bullet section -- the heading and the interface line are built from
# `ListingDiff.a`/`.b` directly).
_SECTION_ORDER = ("items", "units", "boundary", "conductors", "mates", "nets")


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


def _changed_clause(row: Change) -> str:
    """One changed field: `m A to B`, or `m set to B` when it was empty (reports-0006)."""
    if not row.before:
        return f"{row.field} set to {row.after}"
    return f"{row.field} {row.before} to {row.after}"


def _bullet(section: str, rows: list[Change]) -> str:
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
    clauses.extend(_changed_clause(row) for row in rows if row.change == "changed")
    return f"- Changed {identity}: {'; '.join(clauses)}."


def _subject_groups(rows: list[Change]) -> list[list[Change]]:
    """`rows` (one section, already sorted by subject) split into consecutive same-subject runs."""
    groups: list[list[Change]] = []
    for row in rows:
        if groups and groups[-1][0].subject == row.subject:
            groups[-1].append(row)
        else:
            groups.append([row])
    return groups


def _sections(changes: tuple[Change, ...]) -> list[tuple[str, list[list[Change]]]]:
    """`changes` split into `(section, subject_groups)` pairs, in `_SECTION_ORDER`, `unit` out."""
    by_section: dict[str, list[Change]] = {}
    for change in changes:
        if change.section == "unit":
            continue
        by_section.setdefault(change.section, []).append(change)
    return [
        (section, _subject_groups(by_section[section]))
        for section in _SECTION_ORDER
        if section in by_section
    ]


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
        lines.extend(["", f"Interface {diff.a.interface} to {diff.b.interface}."])
    sections = _sections(diff.changes)
    if not sections:
        lines.extend(["", "No changes."])
        return "\n".join(lines)
    for section, subject_groups in sections:
        lines.extend(["", f"## {section.title()}", ""])
        lines.extend(_bullet(section, rows) for rows in subject_groups)
    return "\n".join(lines)
