"""`index_ids`: pairs grouped by key, keys and members in `Id` order, whatever their arrival."""

from typing import Any

from fransys_model.kernel import Id, index_ids


def _id(kind: str, value: str) -> Id[Any]:
    return Id(kind=kind, value=value)


_A, _B, _C = _id("unit", "a"), _id("unit", "b"), _id("unit", "c")
_X, _Y, _Z = _id("item", "x"), _id("item", "y"), _id("item", "z")


def test_keys_and_members_come_out_in_id_order() -> None:
    grouped = index_ids([(_C, _Z), (_A, _Y), (_C, _X), (_A, _Z), (_A, _X)])
    assert list(grouped) == [_A, _C]
    assert grouped == {_A: (_X, _Y, _Z), _C: (_X, _Z)}
    assert list(grouped.items()) == [(_A, (_X, _Y, _Z)), (_C, (_X, _Z))]


def test_the_order_pairs_arrive_in_does_not_show() -> None:
    pairs = [(_B, _Y), (_A, _Z), (_B, _X), (_A, _X)]
    assert index_ids(pairs) == index_ids(reversed(pairs))
    assert index_ids(pairs) == {_A: (_X, _Z), _B: (_X, _Y)}


def test_an_id_with_no_pair_has_no_entry() -> None:
    grouped = index_ids([(_A, _X)])
    assert _B not in grouped
    assert grouped.get(_B, ()) == ()


def test_no_pairs_is_an_empty_index() -> None:
    assert index_ids([]) == {}


def test_a_repeated_pair_is_kept_and_a_set_of_pairs_drops_it() -> None:
    pairs = [(_A, _X), (_A, _X), (_A, _Y)]
    assert index_ids(pairs) == {_A: (_X, _X, _Y)}
    assert index_ids(set(pairs)) == {_A: (_X, _Y)}


def test_the_index_is_immutable() -> None:
    grouped = index_ids([(_A, _X)])
    assert isinstance(grouped, frozendict)
    assert isinstance(grouped[_A], tuple)
