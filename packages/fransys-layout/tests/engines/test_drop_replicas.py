"""`drop_replicas`: a replica its page does not need is dropped, and nothing moves (layout-0021)."""

import dataclasses

import pytest
from samples import PROFILE, SHEET, column, drawn, hid, page_plan

from fransys_layout.geometry import LayoutError
from fransys_layout.stages import PagePlan, place
from fransys_layout.stages.page_stacking import PageStacking
from fransys_layout.stages.replicate import drop_replicas

_HOME = column("home", (1, 2))
_REPLICA = column("rep", (1,))
_REPLICAS = frozenset({_REPLICA.key})


def _names(plan: PagePlan) -> tuple[str, ...]:
    return tuple(planned.column[-1] for planned in plan.columns)


def _in_set(plan: PagePlan, drawing_set: int) -> PagePlan:
    return dataclasses.replace(plan, drawing_set=drawing_set)


@pytest.mark.parametrize("order", [("home", "rep"), ("rep", "home")])
def test_a_replica_on_the_page_of_its_terminals_home_is_dropped(order: tuple[str, ...]) -> None:
    """The home holds the terminal whichever side of the replica it is on."""
    (plan,) = drop_replicas((page_plan(order),), (_HOME, _REPLICA), replicas=_REPLICAS)
    assert _names(plan) == ("home",)


def test_a_replica_on_a_page_without_the_terminal_is_kept() -> None:
    """Nothing else on the page holds function 1, so its replica stays."""
    other = column("a", (3,))
    (plan,) = drop_replicas((page_plan(("a", "rep")),), (other, _REPLICA), replicas=_REPLICAS)
    assert _names(plan) == ("a", "rep")


def test_of_two_replicas_of_one_terminal_on_a_page_the_first_is_kept() -> None:
    """Column order decides: the left replica holds the terminal, the right one goes."""
    other = column("a", (3,))
    later = column("rep2", (1,))
    columns = (other, _REPLICA, later)
    (plan,) = drop_replicas(
        (page_plan(("a", "rep", "rep2")),), columns, replicas=frozenset({_REPLICA.key, later.key})
    )
    assert _names(plan) == ("a", "rep")


def test_a_replica_on_each_of_two_pages_neither_holding_the_home_is_kept_on_both() -> None:
    """The drop is per page: an earlier page's replica does not drop a later page's."""
    a, b, later = column("a", (3,)), column("b", (4,)), column("rep2", (1,))
    plans = (page_plan(("a", "rep"), number=1), page_plan(("b", "rep2"), number=2))
    result = drop_replicas(
        plans, (a, b, _REPLICA, later), replicas=frozenset({_REPLICA.key, later.key})
    )
    assert [_names(plan) for plan in result] == [("a", "rep"), ("b", "rep2")]


def test_a_page_of_another_drawing_set_never_drops_for_the_home_elsewhere() -> None:
    """The home is in drawing set 1; the replica's page is in set 2, and stays."""
    other = column("a", (3,))
    plans = (page_plan(("home",)), _in_set(page_plan(("a", "rep")), 2))
    result = drop_replicas(plans, (_HOME, other, _REPLICA), replicas=_REPLICAS)
    assert [_names(plan) for plan in result] == [("home",), ("a", "rep")]


def test_survivors_keep_their_index_and_nothing_else_changes() -> None:
    """Nothing is repacked: the gap stays, and groups, title and order are as given."""
    other = column("b", (3,))
    plan = page_plan(("home", "rep", "b"))
    (result,) = drop_replicas((plan,), (_HOME, _REPLICA, other), replicas=_REPLICAS)
    assert [planned.index for planned in result.columns] == [0, 2]
    assert result == dataclasses.replace(plan, columns=(plan.columns[0], plan.columns[2]))


def test_a_column_that_is_not_a_replica_is_never_dropped() -> None:
    """Two ordinary columns holding one function are both kept: only replicas are dropped."""
    twin = column("twin", (1,))
    plan = page_plan(("home", "twin"))
    assert drop_replicas((plan,), (_HOME, twin), replicas=frozenset()) == (plan,)


def test_plans_come_back_in_the_order_given() -> None:
    """Pages are not sorted, merged or dropped: the result lines up with the input."""
    plans = (page_plan(("home",), number=2), page_plan(("home", "rep"), number=1))
    result = drop_replicas(plans, (_HOME, _REPLICA), replicas=_REPLICAS)
    assert [plan.number for plan in result] == [2, 1]


def test_a_plan_with_a_gap_in_its_indices_still_places() -> None:
    """`place` takes the surviving columns of a plan whose index runs 0, 2."""
    other = column("b", (3,))
    columns = (_HOME, _REPLICA, other)
    (plan,) = drop_replicas((page_plan(("home", "rep", "b")),), columns, replicas=_REPLICAS)
    placed, findings = place(
        plan, columns, (drawn(1), drawn(2), drawn(3)), PageStacking(profile=PROFILE, sheet=SHEET)
    )
    assert {one.function for one in placed} == {hid("function", n) for n in (1, 2, 3)}
    assert findings == ()


def test_a_plan_naming_a_column_that_does_not_exist_raises() -> None:
    """Every planned key is a column of the run: anything else is an engine-assembly fault."""
    with pytest.raises(LayoutError):
        drop_replicas((page_plan(("home", "ghost")),), (_HOME,), replicas=frozenset())
