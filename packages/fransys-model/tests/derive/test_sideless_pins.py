"""`derive.sideless_pins`: pin order of a sideless end, and the equal-names verdict (model-0242)."""

from fransys_model.derive import sideless_pins
from fransys_model.kernel import make_id
from fransys_model.vocab import FunctionTemplate, PortRole, PortTemplate


def _pin(name: str, marking: str | None = None) -> PortTemplate:
    key = ("part", "fn", "port", name)
    return PortTemplate(
        id=make_id(PortTemplate, key),
        key=key,
        function=make_id(FunctionTemplate, ("part", "fn")),
        name=name,
        role=PortRole.GENERIC,
        marking=marking,
    )


def _names(pins: tuple[PortTemplate, ...]) -> list[str]:
    return [pin.name for pin in pins]


def test_pins_come_in_marking_order_by_value() -> None:
    out = sideless_pins(
        "X1.a", (_pin("p", "10"), _pin("q", "9")), "X2.a", (_pin("r", "2"), _pin("s", "1"))
    )
    assert _names(out.first) == ["q", "p"]
    assert _names(out.second) == ["s", "r"]
    assert out.problem is None


def test_unmarked_pins_sort_by_name() -> None:
    out = sideless_pins("X1.a", (_pin("B"), _pin("A")), "X2.a", (_pin("D"), _pin("C")))
    assert _names(out.first) == ["A", "B"]
    assert _names(out.second) == ["C", "D"]
    assert out.problem is None


def test_another_pin_count_is_a_problem_naming_both_ends() -> None:
    out = sideless_pins("X1.a", (_pin("1"), _pin("2")), "X2.a", (_pin("1"),))
    assert out.problem == "X1.a has 2 pins and X2.a has 1: name the pins"


def test_the_same_names_in_another_order_is_a_problem() -> None:
    out = sideless_pins(
        "X1.a", (_pin("A", "2"), _pin("B", "1")), "X2.a", (_pin("A", "1"), _pin("B", "2"))
    )
    assert out.problem is not None
    assert "name the same pins in different orders (B, A against A, B)" in out.problem


def test_other_names_in_the_same_count_pair_without_a_problem() -> None:
    out = sideless_pins("X1.a", (_pin("A"), _pin("B")), "X2.a", (_pin("1"), _pin("2")))
    assert out.problem is None
