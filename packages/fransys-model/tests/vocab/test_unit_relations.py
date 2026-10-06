"""model-0152: `in_unit_subtree` and `crosses_unit`, the two unit-boundary facts."""

from typing import TYPE_CHECKING, NamedTuple

from plant import Plant

from fransys_model.vocab.membership import crosses_unit, in_unit_subtree

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Item, Unit


class _Nest(NamedTuple):
    model: Model
    a: Id[Unit]
    in_a: Id[Item]
    in_b: Id[Item]
    in_c: Id[Item]
    bare: Id[Item]


def _nest() -> _Nest:
    """Unit B nested in A, a sibling unit C, and one item in each, plus an item in no unit."""
    plant = Plant()
    a = plant.unit("a")
    b = plant.unit("b", parent=a)
    c = plant.unit("c")
    in_a = plant.item("in-a", unit=a)
    in_b = plant.item("in-b", unit=b)
    in_c = plant.item("in-c", unit=c)
    bare = plant.item("bare")
    return _Nest(plant.model(), a, in_a, in_b, in_c, bare)


def test_in_unit_subtree_reads_the_subtree_of_the_unit() -> None:
    """A sub-unit's item is inside its parent; a sibling's and an unplaced item are not."""
    n = _nest()
    assert in_unit_subtree(n.model, n.in_b, n.a)
    assert in_unit_subtree(n.model, n.in_a, n.a)
    assert not in_unit_subtree(n.model, n.in_c, n.a)
    assert not in_unit_subtree(n.model, n.bare, n.a)


def test_crosses_unit_is_strict_so_the_nested_case_crosses() -> None:
    """An end in sub-unit B of A against an end in A crosses, though B is in A's subtree."""
    n = _nest()
    assert crosses_unit(n.model, n.in_b, n.in_a)
    assert crosses_unit(n.model, n.in_a, n.in_c)
    assert crosses_unit(n.model, n.in_a, n.bare)
    assert not crosses_unit(n.model, n.in_a, n.in_a)
    assert not crosses_unit(n.model, n.bare, n.bare)
    assert in_unit_subtree(n.model, n.in_b, n.a)
