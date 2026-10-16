"""The one components function: connected groups of plain members, joined by groups to join."""

from typing import TYPE_CHECKING

from fransys_model.kernel import UnionFind

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from _typeshed import SupportsRichComparison


def components[K: SupportsRichComparison](
    members: Iterable[K], joins: Iterable[Sequence[K]]
) -> tuple[tuple[K, ...], ...]:
    """Each connected group, sorted with the smallest member first, groups in that order.

    A join is a group of members that become one; the caller chooses which groups to pass,
    so no joining rule lives here. A join member not in `members` is added.
    """
    sets: UnionFind[K] = UnionFind(members)
    for group in joins:
        sets.union_all(group)
    return tuple(sorted(tuple(sorted(found)) for found in sets.groups().values()))
