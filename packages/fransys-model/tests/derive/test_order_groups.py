"""`function_groups_in_order`: profile rank, then natural key, then the authored order hints."""

from typing import Any

from fransys_model.derive import function_groups_in_order
from fransys_model.kernel import Draft, Id, Model, Origin, freeze, make_id
from fransys_model.layout import OrderHint, Profile
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.enums import Aspect

_ORIGIN = Origin(file="test_order_groups.py", line=1, note="fixture")


def _node(key: str, label: str) -> AspectNode:
    return AspectNode(
        id=make_id(AspectNode, (key,)),
        key=(key,),
        aspect=Aspect.FUNCTION,
        parent=None,
        label=label,
        description=f"{label} group",
    )


A1, F2, F10 = _node("A1", "alarms"), _node("F2", "feed"), _node("F10", "pumps")
ALL = frozenset({A1.id, F2.id, F10.id})


def _hint(before: AspectNode, after: AspectNode) -> OrderHint:
    key = ("hint", before.key[0], after.key[0])
    return OrderHint(id=make_id(OrderHint, key), key=key, before=before.id, after=after.id)


def _model(*records: Any) -> Model:
    draft = Draft()
    draft.extend((A1, F2, F10, *records), origin=_ORIGIN)
    return freeze(draft)


def _keys(model: Model, used: frozenset[Id[Any]] = ALL) -> list[str]:
    nodes = {A1.id: "A1", F2.id: "F2", F10.id: "F10"}
    return [nodes[n] for n in function_groups_in_order(model, None, used)]


def test_unranked_groups_follow_the_natural_key() -> None:
    """`F2` before `F10`: the key's number is read as a number."""
    assert _keys(_model()) == ["A1", "F2", "F10"]


def test_a_ranked_label_stands_before_every_unranked_group() -> None:
    """The profile's `group_ranks` keys a group by its label."""
    key = ("profile",)
    ranks = frozendict({"pumps": 0})
    profile = Profile(id=make_id(Profile, key), key=key, group_ranks=ranks)
    assert _keys(_model(profile)) == ["F10", "A1", "F2"]


def test_an_order_hint_moves_its_later_group_after_the_earlier() -> None:
    """`F10` before `A1`: a stable pass keeps the rest in natural order."""
    assert _keys(_model(_hint(F10, A1))) == ["F2", "F10", "A1"]


def test_a_hint_cycle_leaves_every_hint_out() -> None:
    """Two hints that contradict each other order nothing."""
    assert _keys(_model(_hint(F10, A1), _hint(A1, F10))) == ["A1", "F2", "F10"]


def test_only_the_used_groups_come_back_and_a_hint_on_an_unused_one_is_dropped() -> None:
    """A hint naming a group outside `used` moves nothing."""
    used = frozenset({A1.id, F2.id})
    assert _keys(_model(_hint(F10, A1)), used) == ["A1", "F2"]
