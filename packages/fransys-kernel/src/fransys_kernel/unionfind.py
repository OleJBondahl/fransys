"""`UnionFind`: disjoint sets whose root is the smallest member, so no join order shows."""

from typing import TYPE_CHECKING
lazy from collections.abc import Iterable, Sequence

if TYPE_CHECKING:
    from _typeshed import SupportsRichComparison


class UnionFind[K: SupportsRichComparison]:
    """Disjoint sets of hashable, orderable members; the smallest member of a set is its root.

    The root depends only on which members a set holds, never on the order the unions were
    made, so a caller may number or key its groups by root. A member not yet seen is its own
    set on its first `find` or `union`, so a caller may register members up front (the empty
    and one-member sets then show in `groups`) or not.
    """

    def __init__(self, members: Iterable[K] = ()) -> None:
        """Register each of `members` as its own set."""
        self._parent: dict[K, K] = {member: member for member in members}

    def find(self, member: K) -> K:
        """The root of `member`'s set, registering `member` as its own set if it is new."""
        parent = self._parent
        parent.setdefault(member, member)
        while parent[member] != member:
            parent[member] = parent[parent[member]]
            member = parent[member]
        return member

    def union(self, first: K, second: K) -> bool:
        """Join the sets of `first` and `second`; `False` if they were already one set."""
        root_first, root_second = self.find(first), self.find(second)
        if root_first == root_second:
            return False
        low, high = sorted((root_first, root_second))
        self._parent[high] = low
        return True

    def union_all(self, members: Sequence[K]) -> None:
        """Join the sets of every one of `members` to the first's; empty or single is a no-op."""
        for member in members[1:]:
            self.union(members[0], member)

    def groups(self) -> dict[K, list[K]]:
        """Each root with the members of its set.

        The dict and each list follow the order the members were first registered; sort
        them if the caller needs an order that does not depend on registration.
        """
        grouped: dict[K, list[K]] = {}
        for member in self._parent:
            grouped.setdefault(self.find(member), []).append(member)
        return grouped
