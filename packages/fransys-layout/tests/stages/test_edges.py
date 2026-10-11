"""Which edge each interface of a middle outline takes, and their order along it."""

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
    """J2 and J3 would fit after J7 is refused: a skip leaves them on top."""
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


def test_along_orders_by_the_x_of_the_columns_reached() -> None:
    ids = [_id("A"), _id("B"), _id("C")]
    reach = {_id("A"): 300, _id("B"): 100, _id("C"): 200}
    assert along(ids, reach) == (_id("B"), _id("C"), _id("A"))
    assert along(ids, dict.fromkeys(ids, 5)) == tuple(ids)
