"""`UnionFind`: the root is the smallest member whatever order the unions came in."""

import itertools

from fransys_model.kernel import UnionFind

# Two sets, {1, 3, 5} and {2, 4}, built from these joins; 6 stays alone.
_JOINS = ((5, 3), (4, 2), (3, 1), (5, 1))


def test_root_is_smallest_member_for_every_join_order() -> None:
    for order in itertools.permutations(_JOINS):
        for flip in (False, True):
            sets = UnionFind(range(1, 7))
            for first, second in order:
                sets.union(*((second, first) if flip else (first, second)))
            assert {sets.find(member) for member in (1, 3, 5)} == {1}
            assert {sets.find(member) for member in (2, 4)} == {2}
            assert sets.find(6) == 6


def test_union_reports_whether_it_joined() -> None:
    sets = UnionFind([1, 2, 3])
    assert sets.union(2, 1) is True
    assert sets.union(1, 2) is False
    assert sets.union(2, 2) is False
    assert sets.union(3, 2) is True
    assert sets.find(3) == 1


def test_find_registers_an_unseen_member() -> None:
    sets = UnionFind()
    assert sets.find("b") == "b"
    assert sets.union("a", "c") is True
    assert sets.union("c", "b") is True
    assert sets.groups() == {"a": ["b", "a", "c"]}


def test_groups_mix_of_registered_and_unseen() -> None:
    sets = UnionFind([4, 2, 9])
    sets.union(9, 4)
    sets.union(7, 8)
    assert sets.groups() == {4: [4, 9], 2: [2], 7: [7, 8]}


def test_union_all_empty_single_and_many() -> None:
    sets = UnionFind([1, 2, 3, 4])
    sets.union_all(())
    sets.union_all((3,))
    assert sets.groups() == {1: [1], 2: [2], 3: [3], 4: [4]}
    sets.union_all((4, 2, 3))
    assert sets.groups() == {1: [1], 2: [2, 3, 4]}


def test_a_long_chain_keeps_its_answers() -> None:
    size = 500
    sets = UnionFind(range(size))
    for member in range(size - 1, 0, -1):  # each join hangs the chain one deeper
        sets.union(member, member - 1)
    assert all(sets.find(member) == 0 for member in range(size))
    assert all(sets.find(member) == 0 for member in range(size))  # after path halving
    assert list(sets.groups()) == [0]
    assert sets.groups()[0] == list(range(size))
