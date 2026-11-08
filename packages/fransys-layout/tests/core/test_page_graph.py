"""The point graph's reading of ink that the drawing netlist must not trust: bare joints, dotted crossings, wires over pin tips."""

import pytest

from fransys_layout.core import page_graph

H = [(-20, 0), (20, 0)]
V = [(0, -20), (0, 20)]


@pytest.mark.rule("READ-T-DOT")
def test_four_ink_directions_at_a_vertex_with_no_dot_are_a_bare_joint() -> None:
    graph = page_graph([[(-20, 0), (0, 0)], [(0, 0), (20, 0)], [(0, 0), (0, 20)], [(0, 0), (0, -20)]], set(), [])
    assert graph.bare_joints == ((0, 0),)


@pytest.mark.rule("READ-T-DOT")
def test_a_wire_end_on_another_wires_interior_with_no_dot_is_a_bare_joint() -> None:
    assert page_graph([H, [(0, 0), (0, 20)]], set(), []).bare_joints == ((0, 0),)


@pytest.mark.rule("READ-T-DOT")
def test_a_three_way_with_a_dot_or_a_pin_tip_and_a_bare_crossing_are_not_bare_joints() -> None:
    tee = [H, [(0, 0), (0, 20)]]
    assert page_graph(tee, {(0, 0)}, []).bare_joints == ()
    assert page_graph(tee, set(), [(0, 0)]).bare_joints == ()
    assert page_graph([H, V], set(), []).bare_joints == ()


@pytest.mark.rule("READ-DOT-CROSSING")
def test_a_dot_where_two_wires_cross_through_each_other_is_a_dot_crossing() -> None:
    assert page_graph([H, V], {(0, 0)}, []).dot_crossings == ((0, 0),)
    assert page_graph([H, V], set(), []).dot_crossings == ()
    assert page_graph([H, [(0, 0), (0, 20)]], {(0, 0)}, []).dot_crossings == ()


@pytest.mark.rule("READ-WIRE-OVER-TIP")
def test_a_wire_whose_interior_passes_a_pin_tip_is_over_it_and_one_ending_there_is_not() -> None:
    assert page_graph([H], set(), [(0, 0)]).over_tips == (((0, 0), 0),)
    assert page_graph([[(-20, 0), (0, 0)]], set(), [(0, 0)]).over_tips == ()
    assert page_graph([H], {(0, 0)}, [(0, 0)]).over_tips == ()
