"""The identity text of one `Change` bullet (reports-0004), one home for every renderer."""


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
