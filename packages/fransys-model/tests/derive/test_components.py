"""Tests: `components` groups members by joins, and agrees with the kernel `UnionFind`."""

import random

from fransys_model.derive.facts.components import components
from fransys_model.kernel import UnionFind


def test_planted_graph() -> None:
    """Two joined groups, a bridge-free singleton, and a member only a join names."""
    found = components(range(1, 8), [(1, 2), (2, 3), (5, 4), (9, 8)])
    assert found == ((1, 2, 3), (4, 5), (6,), (7,), (8, 9))


def test_join_order_does_not_show() -> None:
    joins = [(3, 1), (2, 3), (6, 5)]
    assert components(range(1, 7), joins) == components(range(1, 7), joins[::-1])


def test_empty_and_single_joins_are_no_ops() -> None:
    assert components("ba", [(), ("a",)]) == (("a",), ("b",))
    assert components((), ()) == ()


def test_agrees_with_union_find_on_random_joins() -> None:
    rng = random.Random(20261016)  # noqa: S311 seeded test data, not security
    for _ in range(200):
        members = list(range(rng.randint(0, 25)))
        joins = [
            tuple(rng.choice(members) for _ in range(rng.randint(0, 4)))
            for _ in range(rng.randint(0, 15) if members else 0)
        ]
        reference = UnionFind(members)
        for group in joins:
            reference.union_all(group)
        expected = sorted(tuple(sorted(g)) for g in reference.groups().values())
        assert components(members, joins) == tuple(expected)
