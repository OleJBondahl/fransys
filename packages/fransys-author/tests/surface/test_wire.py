"""EA wire: `d.wire` builds exactly what the engine's wiring builds."""

from decimal import Decimal

import pytest
from fransys_author import AuthorError
from fransys_author.surface import design

from fransys_model.vocab import Conductor, WireFacet
lazy from fransys_model.kernel import Draft


def _pins(d):
    e = d._engine
    k1 = e.item("TEST-RLY-2CO", tag="K1", name="K1")
    k2 = e.item("TEST-RLY-2CO", tag="K2", name="K2")
    return k1.fn("coil")["A1"], k1.fn("coil")["A2"], k2.fn("coil")["A1"]


def _wires(d) -> list:
    return [r for r in d.draft().records() if isinstance(r, Conductor | WireFacet)]


def _engine_wires(parts: Draft, *, chain=False, **kw) -> list:
    d = design(parts)
    a, b, c = _pins(d)
    maker = d._engine.wiring(colour="BU", gauge="0.75")
    if chain:
        maker.run(a, b, c, **kw)
    else:
        maker(a, b, **kw)
    return _wires(d)


def test_two_pins_build_the_engine_records(parts: Draft) -> None:
    d = design(parts)
    a, b, _ = _pins(d)
    d.wire(a, b, wire=("BU", "0.75"))  # ty: ignore[invalid-argument-type] -- a str mm2 still reads
    got = _wires(d)
    assert got == _engine_wires(parts)
    facet = next(r for r in got if isinstance(r, WireFacet))
    assert (facet.colour, facet.gauge_mm2) == ("BU", Decimal("0.75"))


def test_a_float_gauge_is_read_through_its_text(parts: Draft) -> None:
    d = design(parts)
    a, b, _ = _pins(d)
    d.wire(a, b, wire=("BU", 0.75))
    assert _wires(d) == _engine_wires(parts)


def test_wire_is_one_colour_mm2_tuple(parts: Draft) -> None:
    d = design(parts)
    a, b, _ = _pins(d)
    d.wire(a, b, wire=("BU", 0.75), label="W1")
    assert _wires(d) == _engine_wires(parts, label="W1")


@pytest.mark.parametrize("bad", ["BU", ("BU",), ("BU", 0.75, 1), ["BU", 0.75]])
def test_any_other_form_of_wire_raises(parts: Draft, bad: object) -> None:
    d = design(parts)
    a, b, _ = _pins(d)
    with pytest.raises(AuthorError, match=r"wire= is a \(colour, mm2\) tuple"):
        d.wire(a, b, wire=bad)  # ty: ignore[invalid-argument-type] -- the bad form is the test
    assert not _wires(d)


def test_the_outer_port_of_a_terminal_is_a_wire_end(parts: Draft) -> None:
    d = design(parts)
    a, _, _ = _pins(d)
    t = d._engine.strip("X1").terminal("TEST-TB")
    d.wire(a, t.outer, wire=("BU", 0.75))
    conductor = next(r for r in _wires(d) if isinstance(r, Conductor))
    assert t.outer.id in {conductor.a, conductor.b}
    assert t.inner.id not in {conductor.a, conductor.b}


def test_three_pins_make_a_daisy_chain(parts: Draft) -> None:
    d = design(parts)
    a, b, c = _pins(d)
    d.wire(a, b, c, wire=("BU", 0.75))
    got = _wires(d)
    assert sum(isinstance(r, Conductor) for r in got) == 2
    assert got == _engine_wires(parts, chain=True)


def test_n_reaches_the_conductor_key(parts: Draft) -> None:
    d = design(parts)
    a, b, _ = _pins(d)
    d.wire(a, b, wire=("BU", 0.75), n=2)
    got = _wires(d)
    assert got == _engine_wires(parts, n=2)
    assert "n" in next(r for r in got if isinstance(r, Conductor)).key


def test_a_terminal_is_wired_on_its_inner_side(parts: Draft) -> None:
    d = design(parts)
    a, _, _ = _pins(d)
    t = d._engine.strip("X1").terminal("TEST-TB")
    d.wire(a, t, wire=("BU", 0.75))
    conductor = next(r for r in _wires(d) if isinstance(r, Conductor))
    assert t.inner.id in {conductor.a, conductor.b}
    assert t.outer.id not in {conductor.a, conductor.b}


@pytest.mark.parametrize("colour", ["XX", ""])
def test_an_unknown_colour_raises_with_the_grammar(parts: Draft, colour: str) -> None:
    d = design(parts)
    a, b, _ = _pins(d)
    with pytest.raises(AuthorError, match=rf"colour '{colour}' is not allowed.*IEC 60757"):
        d.wire(a, b, wire=(colour, 0.75))


def test_a_surface_object_or_a_string_is_not_a_pin(parts: Draft) -> None:
    d = design(parts)
    a, _, _ = _pins(d)
    with pytest.raises(AuthorError, match=r"d\.wire joins pins: name one pin, got str"):
        d.wire(a, "K1", wire=("BU", 0.75))  # ty: ignore[invalid-argument-type] -- the bad pin is the test


def test_fewer_than_two_pins_raises(parts: Draft) -> None:
    d = design(parts)
    a, _, _ = _pins(d)
    with pytest.raises(AuthorError, match="at least 2 pins, got 1"):
        d.wire(a, wire=("BU", 0.75))


def test_wire_is_required(parts: Draft) -> None:
    d = design(parts)
    a, b, _ = _pins(d)
    with pytest.raises(TypeError, match="wire"):
        d.wire(a, b)  # ty: ignore[missing-argument] -- the missing wire= is the test
