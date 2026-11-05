"""The one group-by over `(key id, member id)` pairs; every id index asks it."""

lazy from collections.abc import Iterable

lazy from .ids import Id


def index_ids[K, M](pairs: Iterable[tuple[Id[K], Id[M]]]) -> frozendict[Id[K], tuple[Id[M], ...]]:
    """Group `pairs` by their first id; keys and members in `Id` order.

    A key no pair names has no entry. A pair given twice is kept twice: the member appears
    twice in its key's tuple. A caller that wants each member once passes a `set` of pairs.
    """
    grouped: dict[Id[K], list[Id[M]]] = {}
    for key, member in pairs:
        grouped.setdefault(key, []).append(member)
    return frozendict({key: tuple(sorted(grouped[key])) for key in sorted(grouped)})
