"""The `Change` rows every baseline diff section builds the same way."""

from typing import TYPE_CHECKING

from .order import change_key
from .rows_baseline import Change

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping


def presence_changes[K, R](
    section: str,
    a_index: Mapping[K, R],
    b_index: Mapping[K, R],
    describe: Callable[[K, R], tuple[str, tuple[str, ...], str]],
) -> list[Change]:
    """A `removed` row per key only in `a_index`, an `added` row per key only in `b_index`.

    `describe(key, row)` gives the row's `(subject, parts, detail)`.
    """
    found: list[Change] = []
    for kind, index, keys in (("removed", a_index, set(a_index) - set(b_index)), ("added", b_index, set(b_index) - set(a_index))):
        for key in keys:
            subject, parts, detail = describe(key, index[key])
            found.append(Change(section=section, change=kind, subject=subject, field="", before="", after="", parts=parts, detail=detail))
    return found


def sort_changes(changes: list[Change]) -> list[Change]:
    """`changes` by subject in natural order, then field."""
    changes.sort(key=change_key)
    return changes
