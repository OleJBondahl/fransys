"""`group_order`: profile ranks first, then natural order, then the order hints (spec O4)."""

import pytest
from samples import hid

from fransys_layout.geometry import HintError
from fransys_layout.stages import GroupInfo, OrderHint, group_order


def info(number: int, label: str, order: int = 0) -> GroupInfo:
    """A group `number` labelled `label`, at natural rank `order`."""
    return GroupInfo(
        group=hid("aspect_node", number),
        key=("invented", label),
        label=label,
        description="",
        order=order,
    )


def hint(before: int, after: int) -> OrderHint:
    """Group `before` goes ahead of group `after`."""
    return OrderHint(before=hid("aspect_node", before), after=hid("aspect_node", after))


def labels(ordered: list[GroupInfo]) -> list[str]:
    """The labels in order."""
    return [item.label for item in ordered]


A, B, C = info(1, "A", 0), info(2, "B", 1), info(3, "C", 2)


def test_ranked_first_then_unranked_by_natural_order():
    ranks = frozendict({"C": 0, "B": 1})
    got = group_order([A, B, C], group_ranks=ranks, order_hints=())
    assert labels(got) == ["C", "B", "A"]
    assert labels(group_order([C, B, A], group_ranks=frozendict(), order_hints=())) == list("ABC")


def test_hint_reverses_two_groups():
    got = group_order([A, B, C], group_ranks=frozendict(), order_hints=(hint(2, 1),))
    assert labels(got) == ["B", "A", "C"]


def test_hint_naming_absent_group_changes_nothing():
    got = group_order([A, B, C], group_ranks=frozendict(), order_hints=(hint(9, 1),))
    assert labels(got) == ["A", "B", "C"]


def test_hint_cycle_raises():
    with pytest.raises(HintError):
        group_order([A, B], group_ranks=frozendict(), order_hints=(hint(1, 2), hint(2, 1)))
