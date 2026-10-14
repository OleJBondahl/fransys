"""Copies left out for want of a wire (layout-0214).

A copy is dropped only when no wire draws it, so a wire to an undrawn or
unreachable end keeps every copy. These cases pin each branch of that rule.
"""

import dataclasses

from samples import column, function_spec, hid

from fransys_layout.stages.types import Column, GroupSet, Home, OrderHint, PageHints
from fransys_layout.stages.wired_copies import (
    emptied_groups,
    loose_groups,
    without_groups,
    without_unwired_copies,
)

f1, f2, f3, f9 = hid("function", 1), hid("function", 2), hid("function", 3), hid("function", 9)
g1, g2, g3 = hid("aspect_node", 1), hid("aspect_node", 2), hid("aspect_node", 3)
unit7 = hid("unit", 7)


def _replica(col: Column, index: int) -> Column:
    """`col` with the cell at `index` marked as a copy drawn elsewhere."""
    cells = list(col.cells)
    cells[index] = dataclasses.replace(cells[index], home=Home.ELSEWHERE)
    return dataclasses.replace(col, cells=tuple(cells))


def test_copy_with_wire_in_far_group_keeps_that_copy_only() -> None:
    """A home copy whose wire is drawn at the replica drops; the replica stays."""
    jb = column("jb", (1,), group=1)
    st = _replica(column("st", (1, 2), group=2), 0)
    result = without_unwired_copies((jb, st), {f1}, ((f1, f2),), set())
    assert result == (st,)


def test_home_draws_its_own_wire_and_keeps_both_cells() -> None:
    """A home with a wire to a device in its own column keeps its copy beside the replica."""
    jb = column("jb", (1, 3), group=1)
    st = _replica(column("st", (1, 2), group=2), 0)
    result = without_unwired_copies((jb, st), {f1}, ((f1, f2), (f1, f3)), set())
    assert result == (jb, st)


def test_terminal_with_no_pair_is_dropped() -> None:
    """A terminal under the rule with no wire at all goes with its column."""
    t = column("t", (1,), group=1)
    assert without_unwired_copies((t,), {f1}, (), set()) == ()


def test_kept_terminal_stays_without_a_pair() -> None:
    """A terminal the caller keeps whatever its wires stays, even with no pair."""
    t = column("t", (1,), group=1)
    assert without_unwired_copies((t,), {f1}, (), {f1}) == (t,)


def test_wire_to_undrawn_far_end_keeps_every_copy() -> None:
    """A wire whose far end stands in no column keeps all copies of the terminal."""
    jb = column("jb", (1,), group=1)
    st = _replica(column("st", (1,), group=2), 0)
    columns = (jb, st)
    assert without_unwired_copies(columns, {f1}, ((f1, f9),), set()) == columns


def test_copies_in_a_set_without_the_far_end_keep_every_copy() -> None:
    """A terminal that leaves every drawing set it has a copy in keeps all its copies."""
    a = column("a", (1,), group=1)
    b = dataclasses.replace(column("b", (2,), group=2), unit=unit7)
    columns = (a, b)
    assert without_unwired_copies(columns, {f1}, ((f1, f2),), set()) == columns


def test_replica_in_another_set_drops_and_home_stays() -> None:
    """A box replica in another drawing set drops when the home draws the wire."""
    inn = column("in", (1, 2), group=1)
    box = dataclasses.replace(_replica(column("box", (1,)), 0), unit=unit7)
    result = without_unwired_copies((inn, box), {f1}, ((f1, f2),), set())
    assert result == (inn,)


def test_function_outside_under_is_never_dropped() -> None:
    """A function the rule does not name keeps its cells even with no pairs."""
    x = column("x", (2,), group=1)
    assert without_unwired_copies((x,), set(), (), set()) == (x,)


def test_emptied_group_is_returned() -> None:
    """A group whose only column is gone after the pass is reported."""
    a = column("a", (1,), group=1)
    b = column("b", (2,), group=2)
    assert emptied_groups((a, b), (a,)) == frozenset({g2})


def test_a_loose_functions_group_with_no_column_is_returned() -> None:
    """layout-0218: a group holding a loose function and left with no column is reported.

    # UNDO: stages/wired_copies.py `loose_groups` returns `frozenset()`
    """
    kept = column("a", (1,), group=1)
    loose = (function_spec(2, group=1), function_spec(3, group=2), function_spec(4, group=None))
    assert loose_groups(loose, (kept,)) == frozenset({g2})


def test_none_group_is_never_returned() -> None:
    """A column with no group that disappears does not report a group."""
    n = column("n", (1,), group=None)
    assert emptied_groups((n,), ()) == frozenset()


def test_taken_out_group_leaves_hints_and_bridges_order() -> None:
    """Taking out g2 drops its break, trims its keep-together, and bridges the order past it."""
    hints = PageHints(
        keep_together=(GroupSet(groups=(g1, g2)),),
        break_before=(g2,),
        order=(OrderHint(before=g1, after=g2), OrderHint(before=g2, after=g3)),
    )
    result = without_groups(hints, {g2})
    assert result.break_before == ()
    assert result.keep_together == (GroupSet(groups=(g1,)),)
    assert result.order == (OrderHint(before=g1, after=g3),)


def test_no_groups_returns_hints_unchanged() -> None:
    """An empty set of groups hands the same hints back."""
    hints = PageHints(keep_together=(), break_before=(g1,), order=())
    assert without_groups(hints, set()) is hints


def test_a_seat_keeps_its_copy_and_the_others_drop() -> None:
    """A copy the caller seats (a stub's seat) draws an end; the box copy elsewhere goes."""
    home = column("home", (1,), group=1)
    box = _replica(dataclasses.replace(column("box", (1,), group=1), unit=unit7), 0)
    assert without_unwired_copies((home, box), {f1}, (), set(), {(f1, 0)}) == (home,)


def test_a_seat_beside_a_pair_keeps_both_copies() -> None:
    """A seated home and a replica that draws a wire both stay."""
    home = column("home", (1,), group=1)
    st = _replica(column("st", (1, 2), group=2), 0)
    result = without_unwired_copies((home, st), {f1}, ((f1, f2),), set(), {(f1, 0)})
    assert result == (home, st)


def test_a_fan_out_to_two_groups_keeps_the_home_beside_its_replicas() -> None:
    """Two replicas of one set draw: the home stays, so one copy per page can join them."""
    home = column("home", (1,), group=1)
    a = _replica(column("a", (1, 2), group=2), 0)
    b = _replica(column("b", (1, 3), group=3), 0)
    result = without_unwired_copies((home, a, b), {f1}, ((f1, f2), (f1, f3)), set())
    assert result == (home, a, b)
