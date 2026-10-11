"""Cutting a sequence ordered along an axis into runs."""

from itertools import pairwise
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

    from _typeshed import SupportsDunderLT


def cut_runs[T, K: SupportsDunderLT[Any]](
    items: Iterable[T], key: Callable[[T], K], cuts: Sequence[K]
) -> list[list[T]]:
    """`items`, in `key` order, in runs: a run starts where a cut lies strictly between two."""
    ordered = list(items)
    if not ordered:
        return []
    runs: list[list[T]] = [[ordered[0]]]
    for before, one in pairwise(ordered):
        if any(key(before) < at < key(one) for at in cuts):
            runs.append([])
        runs[-1].append(one)
    return runs
