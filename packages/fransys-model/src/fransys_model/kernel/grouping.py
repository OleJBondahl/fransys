"""The one group-by over `(key id, member id)` pairs (REVIEW-M M6); every id index asks it."""

from typing import Any
lazy from collections.abc import Iterable

lazy from .ids import Id


def index_ids[K](pairs: Iterable[tuple[Id[K], Id[Any]]]) -> frozendict[Id[K], tuple[Id[Any], ...]]:
    """Group `pairs` by their first id; keys and members in `Id` order.

    A key no pair names has no entry. A pair given twice is kept twice: the member appears
    twice in its key's tuple. A caller that wants each member once passes a `set` of pairs.
    """
    grouped: dict[Id[K], list[Id[Any]]] = {}
    for key, member in pairs:
        grouped.setdefault(key, []).append(member)
    return frozendict({key: tuple(sorted(grouped[key])) for key in sorted(grouped)})
