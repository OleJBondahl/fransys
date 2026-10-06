"""EA5: the pole rule and `pair`, each rule with a case that breaks when the rule does."""

from typing import TYPE_CHECKING, Any

import pytest
from fransys_author import AuthorError
from fransys_author.surface import design
from fransys_author.surface._pairing import End, PartFacts, ends_of, pair, poles

from fransys_model.kernel import make_id
from fransys_model.vocab import ConductorMark, FunctionKind, PartCategory, PortRole, PortTemplate

from ..conftest import _ORIGIN, _function, _library, _part  # noqa: TID252 -- importlib mode puts tests/ on no path
from ..equivalence.series_parts import L1, L2, L3, breaker, series_library  # noqa: TID252 -- same

if TYPE_CHECKING:
    from fransys_author.surface import Design

    from fransys_model.kernel import Draft

REVERSED = [("3", "4"), ("1", "2"), ("5", "6")]


@pytest.fixture
def lib() -> Draft:
    """The series library plus a breaker declaring its poles 3/4 first and one with no sides."""
    draft = series_library()
    variants = _library(draft, "test-variants")
    breaker(draft, variants, "TEST-MCB-REV", REVERSED)
    breaker(draft, variants, "TEST-MCB-NOSIDE", sides=False)
    return draft


def _names(pairs: list[tuple[Any, Any]]) -> list[tuple[str, str]]:
    return [(a.name, b.name) for a, b in pairs]


def _fn(d: Design, tag: str, mpn: str, function: str) -> tuple[PartFacts, Any]:
    """The facts of `d` and the engine function `tag.function` (the surface `Fn` wraps it)."""
    fn = getattr(d.device(tag, mpn), function)._fn
    return PartFacts(d.library, d.draft()), fn


def test_three_poles_pair_by_position(lib: Draft) -> None:
    d = design(lib, place="C1")
    facts, q1 = _fn(d, "Q1", "TEST-MCB-3P", "main")
    _, k1 = _fn(d, "K1", "TEST-KM-3P", "main")
    source, load = ends_of(facts, q1).load, ends_of(facts, k1).line
    assert _names(pair(source, load)) == [("2", "1"), ("4", "3"), ("6", "5")]
    assert _names(pair(source[::-1], load)) != _names(pair(source, load))


def test_a_breakers_poles_come_in_model_order_not_declaration_order(lib: Draft) -> None:
    d = design(lib, place="C1")
    facts, q1 = _fn(d, "Q1", "TEST-MCB-REV", "main")
    assert [line.name for line, _ in poles(facts, q1)] == ["1", "3", "5"]
    assert [load.name for _, load in poles(facts, q1)] == ["2", "4", "6"]


def test_a_contactors_main_has_three_poles_and_its_aux_one(lib: Draft) -> None:
    d = design(lib, place="C1")
    facts, main = _fn(d, "K1", "TEST-KM-3P", "main")
    _, aux = _fn(d, "K3", "TEST-KM-3P", "aux")
    assert _names(poles(facts, main)) == [("1", "2"), ("3", "4"), ("5", "6")]
    assert _names(poles(facts, aux)) == [("13", "14")]


def test_a_coil_is_one_pole_from_its_line_and_load_pins(lib: Draft) -> None:
    d = design(lib, place="C1")
    facts, coil = _fn(d, "K1", "TEST-KM-3P", "coil")
    assert _names(poles(facts, coil)) == [("A1", "A2")]
    _, plain = _fn(d, "K2", "TEST-COIL", "coil")
    assert poles(facts, plain) == []  # no side fact and no mark: it is not a pole


def test_a_one_port_function_is_one_pole_ending_the_series(lib: Draft) -> None:
    d = design(lib, place="C1")
    facts, through = _fn(d, "F1", "TEST-OL-3P", "pass")
    _, channel = _fn(d, "A1", "TEST-PLC-CH", "channel")
    assert _names(poles(facts, through)) == [("A2", "A2")]
    assert _names(poles(facts, channel)) == [("CH", "CH")]


def test_a_motor_pairs_by_its_marks_and_keeps_its_pe_apart(lib: Draft) -> None:
    d = design(lib, place="C1")
    facts, motor = _fn(d, "M1", "TEST-MOTOR-3P", "load")
    ends = ends_of(facts, motor)
    assert [e.mark for e in ends.line] == [ConductorMark.L1, ConductorMark.L2, ConductorMark.L3]
    assert ends.line == ends.load
    assert ends.pe is not None
    assert ends.pe.name == "PE"
    _, k1 = _fn(d, "K1", "TEST-KM-3P", "main")
    marked = [End(e.port, m) for e, m in zip(ends_of(facts, k1).load, ConductorMark, strict=False)]
    assert _names(pair(marked[::-1], ends.line)) == [("2", "U"), ("4", "V"), ("6", "W")]


def test_ac_marks_pair_in_phase_order_whatever_the_order_given(lib: Draft) -> None:
    d = design(lib, place="C1")
    facts, motor = _fn(d, "M1", "TEST-MOTOR-3P", "load")
    _, q1 = _fn(d, "Q1", "TEST-MCB-3P", "main")
    l1, l2, l3 = (
        End(e.port, m) for e, m in zip(ends_of(facts, q1).load, ConductorMark, strict=False)
    )
    got = pair([l3, l1, l2], ends_of(facts, motor).line)
    assert _names(got) == [("2", "U"), ("4", "V"), ("6", "W")]
    n = End(l3.port, ConductorMark.N)
    with pytest.raises(AuthorError, match=r"conductors L1, L2, N into L1, L2, L3"):
        pair([l1, l2, n], ends_of(facts, motor).line)


def test_a_pole_with_a_link_and_no_side_fact_says_name_its_pins(lib: Draft) -> None:
    d = design(lib, place="C1")
    facts, q1 = _fn(d, "Q1", "TEST-MCB-NOSIDE", "main")
    with pytest.raises(AuthorError, match=r"'main' pole 1/2 has no line side: name its pins"):
        poles(facts, q1)


def test_a_count_mismatch_names_both_counts(lib: Draft) -> None:
    d = design(lib, place="C1")
    facts, q1 = _fn(d, "Q1", "TEST-MCB-3P", "main")
    _, coil = _fn(d, "K1", "TEST-KM-3P", "coil")
    with pytest.raises(AuthorError, match=r"^3 poles into 1: name the pins$"):
        pair(ends_of(facts, q1).load, ends_of(facts, coil).line)
    assert len(pair(ends_of(facts, coil).load, ends_of(facts, coil).line)) == 1


def test_link_less_marked_pins_come_in_marking_order_not_mark_order(lib: Draft) -> None:
    """P1 (marking 10, L1), P2 (9, L2), P3 (11, L3): marking order P2 P1 P3, mark order P1 P2 P3."""
    part = _part(
        lib, _library(lib, "test-marked"), manufacturer="TestCo", mpn="TEST-MARKED",
        category=PartCategory.ELECTROMECHANICAL, letter="M",
    )  # fmt: skip
    load = _function(lib, part, "load", FunctionKind.LOAD)
    for name, marking, mark in (("P1", "10", L1), ("P2", "9", L2), ("P3", "11", L3)):
        key = (*load.key, "port", name)
        port = PortTemplate(
            id=make_id(PortTemplate, key), key=key, function=load.id, name=name,
            role=PortRole.GENERIC, marking=marking, conductor_mark=mark,
        )  # fmt: skip
        lib.add(port, origin=_ORIGIN)
    d = design(lib, place="C1")
    facts, fn = _fn(d, "M1", "TEST-MARKED", "load")
    assert [line.name for line, _ in poles(facts, fn)] == ["P2", "P1", "P3"]
