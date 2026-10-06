"""The one order of unit releases and of history entries (FD4, SC2)."""

type ReleaseOrder = tuple[int, int]


def release_order(version: int, revision: int) -> ReleaseOrder:
    """`(version, revision)`: the ONE order of unit releases and of history entries.

    The plain pair of two ints, never the printed text: `(1, 9) < (1, 10) < (2, 1)`, where the
    text `"1.10"` would sort before `"1.9"`. Every later pin-source and previous-release
    selection calls this function and never compares revisions again.
    """
    return (version, revision)


def same_version(previous: tuple[str, int], current: tuple[str, int]) -> bool:
    """Whether two releases are the same name and version; `revision` is never compared.

    `previous`/`current` are each `(name, version)`, read straight off whichever record the
    caller has (`UnitRelease`, a stored listing's `unit`, a release target) -- never a new
    record type of its own.
    """
    return previous == current
