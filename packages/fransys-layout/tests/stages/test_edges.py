"""HL13, HL14: which edge each interface of a middle outline takes, and their order along it."""

from fractions import Fraction

from fransys_layout.stages.edges import BOTTOM, TOP, InterfaceEdge, _moves, along, edges
from fransys_model.derive import natural_key
from fransys_model.kernel import Id

Q = Fraction


def _id(name: str) -> Id:
    return Id(kind="function", value=name)


def _line(
    name: str, width: Fraction, share: Fraction, *, hint: bool | None = None
) -> InterfaceEdge:
    return InterfaceEdge(
        _id(name),
        f"-U1-{name}",
        natural_key(f"-U1-{name}"),
        hint,
        line=True,
        share=share,
        width=width,
    )


def _board(*, j3_hint: bool | None = None) -> list[InterfaceEdge]:
    """The spec's worked example: widths 3, 1, 2, 2, 1/2 and shares 4/8, 2/4, 4/12, 0, 0."""
    return [
        _line("J1", Q(3), Q(4, 8)),
        _line("J5", Q(1), Q(2, 4)),
        _line("J7", Q(2), Q(4, 12)),
        _line("J2", Q(2), Q(0)),
        _line("J3", Q(1, 2), Q(0), hint=j3_hint),
    ]


def test_the_worked_example_puts_j1_and_j5_on_top_and_stops_at_j7() -> None:
    """Acceptance 13. J2 and J3 would fit after J7 is refused: a skip leaves them on top."""
    split, trail = _moves(_board())
    assert trail == [
        (_id("J1"), Q(3), Q(11, 2)),
        (_id("J5"), Q(4), Q(9, 2)),
        (_id("J7"), Q(6), Q(5, 2)),
    ]
    assert {k.value: v for k, v in edges(_board()).items()} == {
        "J1": TOP,
        "J5": TOP,
        "J7": BOTTOM,
        "J2": BOTTOM,
        "J3": BOTTOM,
    }
    assert split[_id("J1")] is TOP


def test_a_hint_on_j3_puts_it_on_top_with_j1_and_j5_at_4_5_against_4() -> None:
    split, trail = _moves(_board(j3_hint=TOP))
    assert [k.value for k, v in split.items() if v is TOP] == ["J3", "J1", "J5"]
    assert trail[1][1:] == (Q(9, 2), Q(4))


def test_an_interface_with_no_line_keeps_its_flow_edge() -> None:
    """Acceptance 14, pure half: B balanced as a line interface would go below."""
    a = _line("A", Q(1), Q(1))
    b = InterfaceEdge(_id("B"), "-U1-B", (), None, line=False, share=Q(0), flow=TOP, width=Q(1))
    assert edges([a, b]) == {_id("A"): BOTTOM, _id("B"): TOP}
    assert edges([a, _line("B", Q(1), Q(0))]) == {_id("A"): TOP, _id("B"): BOTTOM}


def test_a_no_line_interface_without_a_flow_goes_below() -> None:
    b = InterfaceEdge(_id("B"), "-U1-B", (), None, line=False, share=Q(1), width=Q(1))
    assert edges([b]) == {_id("B"): BOTTOM}


def test_a_hinted_interface_keeps_its_hint_against_the_balance() -> None:
    """Acceptance 15: the hint puts the heavy one on top and the light one below."""
    heavy = _line("A", Q(3), Q(0), hint=TOP)
    light = _line("B", Q(1), Q(1), hint=BOTTOM)
    assert edges([heavy, light]) == {_id("A"): TOP, _id("B"): BOTTOM}


def test_a_lone_supply_goes_on_top_and_a_lone_output_stays_below() -> None:
    assert edges([_line("A", Q(1), Q(1, 2))]) == {_id("A"): TOP}
    assert edges([_line("A", Q(1), Q(1, 3))]) == {_id("A"): BOTTOM}


def test_equal_shares_rank_by_designation() -> None:
    both = [_line("J2", Q(1), Q(1)), _line("J1", Q(1), Q(1))]
    assert edges(both) == {_id("J2"): BOTTOM, _id("J1"): TOP}


def test_along_orders_by_the_x_of_the_columns_reached() -> None:
    ids = [_id("A"), _id("B"), _id("C")]
    reach = {_id("A"): 300, _id("B"): 100, _id("C"): 200}
    assert along(ids, reach) == (_id("B"), _id("C"), _id("A"))
    assert along(ids, dict.fromkeys(ids, 5)) == tuple(ids)


def test_a_refusal_stops_the_split_though_a_later_interface_would_fit() -> None:
    """Y alone would even the edges (11 against 30), but X is refused first, so Y stays below."""
    fixed = _line("F", Q(10), Q(0), hint=TOP)
    x = _line("X", Q(30), Q(1))
    y = _line("Y", Q(1), Q(0))
    assert edges([fixed, x, y]) == {_id("F"): TOP, _id("X"): BOTTOM, _id("Y"): BOTTOM}


def test_equal_shares_rank_by_designation_in_natural_order() -> None:
    """J2 ranks before J10, so J2 takes the top though J10 is listed first."""
    both = [_line("J10", Q(1), Q(1)), _line("J2", Q(1), Q(1))]
    assert edges(both) == {_id("J10"): BOTTOM, _id("J2"): TOP}
