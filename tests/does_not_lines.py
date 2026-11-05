"""The "Does not" docstring-line check shared by the public-surface docstring tests."""


def has_does_not(doc: str | None) -> bool:
    """True when one line of `doc` starts with "Does not"."""
    return any(line.strip().startswith("Does not") for line in (doc or "").splitlines())
