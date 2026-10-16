"""The identity and the change words of one `Change` row (reports-0004, model-0279), one home."""

from .rows_baseline import Change  # noqa: TC001 -- signature tests resolve hints at runtime


def change_identity(section: str, parts: tuple[str, ...]) -> str:
    """A `Change.parts` tuple as the bullet's identity text.

    One home for the shape so a report never rebuilds it; the parts are never parsed.
    """
    if section == "units":
        instance, name = parts
        return f"`{instance}` ({name})"
    if section in ("conductors", "mates"):
        a, b = parts
        return f"between `{a}` and `{b}`"
    (subject,) = parts
    return f"`{subject}`"


def change_clause(row: Change) -> str:
    """The words for what one `Change` row did: `added`, `removed`, `m A → B` or `m set to B`.

    One home for the wording so the change note and the stale-baseline cause never spell it twice.
    """
    if row.change in ("added", "removed"):
        return row.change
    if not row.before:
        return f"{row.field} set to {row.after}"
    return f"{row.field} {_before_after(row.before, row.after)}"


def _before_after(before: str, after: str) -> str:
    """`before → after`: the one spelling of a change from one value to another."""
    return f"{before} → {after}"


def renamed_text(row: Change) -> str:
    """The note line of a `renamed` row: both designations from `parts`, never parsed."""
    old, new = row.parts
    return f"Renamed `{old}` → `{new}`."


def interface_text(before: str, after: str) -> str:
    """The note line of an interface change: `Interface 1 → 2.`."""
    return f"Interface {_before_after(before, after)}."
