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
    """The words for what one `Change` row did: `added`, `removed`, `m A to B` or `m set to B`.

    One home for the wording so the change note and the stale-baseline cause never spell it twice.
    """
    if row.change in ("added", "removed"):
        return row.change
    if not row.before:
        return f"{row.field} set to {row.after}"
    return f"{row.field} {row.before} to {row.after}"
