"""The union-find behind the placement constraints: offsets, refusals, no recursion, size."""

from fransys_layout.core.unionfind import UnionFind


def test_union_then_find_carries_the_offset() -> None:
    """union(a, b, 8) puts b 8 from a's root; a disagreeing union is refused and changes nothing."""
    uf = UnionFind()
    assert uf.union("a", "b", 8)
    assert uf.find("b") == (uf.find("a")[0], uf.find("a")[1] + 8)
    assert not uf.union("a", "b", 9)
    assert uf.find("b") == (uf.find("a")[0], uf.find("a")[1] + 8)


def test_a_chain_of_5000_unions_finds_without_recursion_error() -> None:
    """A 5000-link chain of offsets is found from its far end with no RecursionError."""
    uf = UnionFind()
    for i in range(5000):
        assert uf.union(f"n{i}", f"n{i + 1}", 1)
    root, offset = uf.find("n5000")
    assert (root, offset) == (uf.find("n0")[0], 5000)


def test_union_by_size_keeps_the_root_of_the_larger_class() -> None:
    """A singleton joined to a three-member class leaves the class's root as the root."""
    uf = UnionFind()
    uf.union("r", "p", 0)
    uf.union("r", "q", 0)
    assert uf.find("r")[0] == "r"
    uf.union("s", "r", 0)
    assert uf.find("s")[0] == "r"
    assert uf.find("p")[0] == "r"
