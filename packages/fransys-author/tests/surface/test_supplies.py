"""EA6: `ac_supply` and `dc_supply` write what the same calls by hand write, and fail by name."""

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from fransys_author import AuthorError
from fransys_author.surface import design
from fransys_author.surface._pairing import End

from fransys_model.kernel import make_id
from fransys_model.vocab import (
    ConductorMark,
    Earthing,
    FunctionKind,
    Net,
    Operating,
    OperatingFacet,
    PartCategory,
    SupplySystem,
)

from ..conftest import _ORIGIN, _function, _library, _part  # noqa: TID252 -- importlib mode puts tests/ on no path
from ..equivalence.series_parts import MINUS, PLUS, _pin, series_library  # noqa: TID252 -- same

if TYPE_CHECKING:
    from fransys_author.surface import Design

    from fransys_model.kernel import Draft

M = ConductorMark.M


def _psu(draft: Draft, mpn: str, marks: dict[str, ConductorMark | None], volts: str | None) -> None:
    """A PSU `out` function with one pin per `marks` item and `volts` as its nominal voltage."""
    lib = _library(draft, f"lib-{mpn}")
    part = _part(
        draft, lib, manufacturer="TestCo", mpn=mpn, category=PartCategory.GENERIC, letter="G"
    )
    out = _function(draft, part, "out", FunctionKind.SUPPLY)
    for name, mark in marks.items():
        _pin(draft, out, name, None, mark)
    if volts is not None:
        key = (*out.key, "operating")
        facet = OperatingFacet(
            id=make_id(OperatingFacet, key),
            key=key,
            subject=out.id,
            operating=Operating(nominal_voltage_v=Decimal(volts)),
        )
        draft.add(facet, origin=_ORIGIN)


@pytest.fixture(scope="module")
def lib() -> Draft:
    """The series library plus PSU variants: a mid pin, no voltage, no marks, a '24.0' voltage."""
    draft = series_library()
    _psu(draft, "PSU-MID", {"B": M, "A": MINUS, "C": PLUS}, "12")
    _psu(draft, "PSU-NOV", {"+": PLUS, "-": MINUS}, None)
    _psu(draft, "PSU-NOMARK", {"+": None, "-": None}, "24")
    _psu(draft, "PSU-NOMINUS", {"+": PLUS, "-": None}, "24")
    _psu(draft, "PSU-TWO-OUT", {"+": PLUS, "-": MINUS}, "24.0")
    return draft


def _records(d: Design, cls: type) -> list:
    return [r for r in d.draft().records() if isinstance(r, cls)]


def test_ac_supply_equals_the_same_calls_by_hand(lib: Draft) -> None:
    d, hand = design(lib, place="C1"), design(lib, place="C1")
    pins = [d.device(f"A{i}", "TEST-PSU-24V").out["+"] for i in range(4)]
    hand_pins = [hand.device(f"A{i}", "TEST-PSU-24V").out["+"] for i in range(4)]
    ac = d.ac_supply("mains", "400", *pins[:3], n=pins[3], earthing=Earthing.IT)
    hand._engine.supply(
        "mains",
        current="ac",
        rails={
            "L1": ("400", 0),
            "L2": ("400", 120),
            "L3": ("400", 240),
            "N": ("0", None),
        },
        earthing="it",
    )
    for rail, pin in zip(("L1", "L2", "L3", "N"), hand_pins, strict=True):
        hand._engine.net(rail, pin, cls="power", potential=rail)
    for cls in (SupplySystem, Net):
        assert sorted(map(repr, _records(d, cls))) == sorted(map(repr, _records(hand, cls)))
    assert _records(d, SupplySystem)[0].earthing is Earthing.IT
    assert [ac.L1.pin, ac.L2.pin, ac.L3.pin, ac.N.pin] == pins
    assert ac.L2.phase == 120
    assert ac.N.phase is None


def test_ac_supply_takes_a_terminals_inner_pin(lib: Draft) -> None:
    d = design(lib, place="C1")
    strip = d.terminal_strip("X1", "TEST-TERM")
    other = d.device("A1", "TEST-PSU-24V").out["+"]
    ac = d.ac_supply("mains", "230", strip[1], other, other)
    assert ac.L1.pin == strip[1].inner


def test_ac_supply_without_n_has_no_n_and_the_error_lists_the_rails(lib: Draft) -> None:
    d = design(lib, place="C1")
    pin = d.device("A1", "TEST-PSU-24V").out["+"]
    ac = d.ac_supply("mains", "230", pin, pin, pin)
    with pytest.raises(AuthorError, match=r"no rail 'N'; rails: L1, L2, L3"):
        _ = ac.N
    assert "N" not in _records(d, SupplySystem)[0].rails


def test_a_misspelt_rail_raises_and_a_private_name_is_an_attribute_error(lib: Draft) -> None:
    d = design(lib, place="C1")
    pin = d.device("A1", "TEST-PSU-24V").out["+"]
    ac = d.ac_supply("mains", "230", pin, pin, pin)
    with pytest.raises(AuthorError, match=r"no rail 'L4'; rails: L1, L2, L3"):
        _ = ac.L4  # ty: ignore[unresolved-attribute] -- a misspelt rail is a ty error too
    with pytest.raises(AttributeError):
        getattr(ac, "_" + "nothing")
    dc = d.dc_supply("psu", d.device("G1", "TEST-PSU-24V").out)
    with pytest.raises(AuthorError, match=r"no rail 'mid'; rails: plus, minus"):
        _ = dc.mid


def test_earthing_must_be_the_enum(lib: Draft) -> None:
    d = design(lib, place="C1")
    pin = d.device("A1", "TEST-PSU-24V").out["+"]
    with pytest.raises(AuthorError, match=r"Earthing.EARTHED or Earthing.IT, not 'it'"):
        d.ac_supply("mains", "230", pin, pin, pin, earthing="it")  # ty: ignore[invalid-argument-type] -- the case
    assert not _records(d, SupplySystem)


def test_ac_rails_stand_in_a_series_as_ends_in_phase_order(lib: Draft) -> None:
    d = design(lib, place="C1")
    pins = [d.device(f"A{i}", "TEST-PSU-24V").out["+"] for i in range(4)]
    ac = d.ac_supply("mains", "400", *pins[:3], n=pins[3])
    ends = ac._series_ends(d, None)
    assert ac._series_width() == 4
    assert ends.line == ends.load
    assert [e.port for e in ends.line] == pins
    assert [e.mark for e in ends.line] == list(ConductorMark)[:4]
    assert ac.L1._series_width() == 1
    assert ac.L1._series_ends(d, 1).line == (End(pins[0], ConductorMark.L1),)


def test_dc_supply_equals_the_same_calls_by_hand(lib: Draft) -> None:
    d, hand = design(lib, place="C1"), design(lib, place="C1")
    g1 = d.device("G1", "TEST-PSU-24V")
    h1 = hand.device("G1", "TEST-PSU-24V")
    d.dc_supply("psu", g1, earthing=Earthing.IT)
    hand._engine.supply(
        "psu",
        current="dc",
        rails={"24V": (Decimal(24), None), "0V": ("0", None)},
        earthing="it",
    )
    hand._engine.net("24V", h1.out["+"], cls="power", potential="24V")
    hand._engine.net("0V", h1.out["-"], cls="power", potential="0V")
    for cls in (SupplySystem, Net):
        assert sorted(map(repr, _records(d, cls))) == sorted(map(repr, _records(hand, cls)))


def test_dc_rails_follow_the_conductor_marks(lib: Draft) -> None:
    d = design(lib, place="C1")
    g1 = d.device("G1", "PSU-MID")
    dc = d.dc_supply("psu", g1)
    assert dc.plus.pin.name == "C"
    assert dc.minus.pin.name == "A"
    assert dc.mid.pin.name == "B"
    assert (dc.plus.mark, dc.minus.mark, dc.mid.mark) == (PLUS, MINUS, M)
    assert (dc.plus.potential, dc.minus.potential, dc.mid.potential) == ("12V", "-12V", "0V")
    (system,) = _records(d, SupplySystem)
    assert {name: rail.max_v for name, rail in system.rails.items()} == {
        "12V": Decimal(12),
        "-12V": Decimal(-12),
        "0V": Decimal(0),
    }
    assert {net.name for net in _records(d, Net)} == {"12V", "-12V", "0V"}


def test_a_source_function_is_enough_and_a_device_with_two_functions_is_ambiguous(
    lib: Draft,
) -> None:
    d = design(lib, place="C1")
    dc = d.dc_supply("psu", d.device("G1", "TEST-PSU-24V").out)
    assert dc.plus.potential == "24V"
    k = d.device("K1", "TEST-KM-3P")
    with pytest.raises(
        AuthorError, match=r"K1 needs exactly one function .*candidates: aux, coil, main"
    ):
        d.dc_supply("bad", k)


def test_the_voltage_is_normalised_in_the_default_name(lib: Draft) -> None:
    d = design(lib, place="C1")
    dc = d.dc_supply("psu", d.device("G1", "PSU-TWO-OUT"))
    assert dc.plus.potential == "24V"


def test_names_override_and_a_third_names_the_mid(lib: Draft) -> None:
    d = design(lib, place="C1")
    dc = d.dc_supply("psu", d.device("G1", "TEST-PSU-24V"), names=("24V", "GND"))
    assert (dc.plus.potential, dc.minus.potential) == ("24V", "GND")
    d2 = design(lib, place="C1")
    dc2 = d2.dc_supply("psu", d2.device("G1", "PSU-MID"), names=("P", "N0", "MID"))
    assert (dc2.plus.potential, dc2.minus.potential, dc2.mid.potential) == ("P", "N0", "MID")
    with pytest.raises(AuthorError, match=r"names= is \(plus, minus\)"):
        d2.dc_supply("x", d2.device("G2", "PSU-MID"), names=("A",))


def test_a_source_without_the_voltage_raises_naming_it(lib: Draft) -> None:
    d = design(lib, place="C1")
    with pytest.raises(AuthorError, match=r"G1\.out lacks nominal voltage$"):
        d.dc_supply("psu", d.device("G1", "PSU-NOV").out)
    assert not _records(d, SupplySystem)


def test_a_voltage_beside_a_stated_nominal_raises_and_dropping_it_builds(lib: Draft) -> None:
    d = design(lib, place="C1")
    with pytest.raises(AuthorError, match=r"^G1 states 12 V: drop voltage=$"):
        d.dc_supply("psu", d.device("G1", "PSU-MID"), voltage=12)
    assert not _records(d, SupplySystem)
    assert d.dc_supply("psu", d.device("G2", "PSU-MID")).plus.potential == "12V"


def test_a_source_without_marks_raises_naming_each_missing_pin(lib: Draft) -> None:
    d = design(lib, place="C1")
    with pytest.raises(AuthorError, match=r"G1\.out lacks L\+ pin, L- pin$"):
        d.dc_supply("psu", d.device("G1", "PSU-NOMARK").out)
    with pytest.raises(AuthorError, match=r"G2\.out lacks L- pin$"):
        d.dc_supply("psu", d.device("G2", "PSU-NOMINUS").out)


def test_plus_and_minus_pins_stand_in_for_missing_marks(lib: Draft) -> None:
    d = design(lib, place="C1")
    g1 = d.device("G1", "PSU-NOMARK")
    dc = d.dc_supply("psu", g1, plus=g1["+"], minus=g1["-"])
    assert (dc.plus.pin.name, dc.minus.pin.name) == ("+", "-")
    assert dc.plus.potential == "24V"


def test_ac_names_rename_the_potentials_and_keep_marks_and_phases(lib: Draft) -> None:
    d = design(lib, place="C1")
    pins = [d.device(f"A{i}", "TEST-PSU-24V").out["+"] for i in range(4)]
    ac = d.ac_supply("it", "133", *pins[:3], n=pins[3], names=("EL1", "EL2", "EL3", "EN"))
    assert [r.potential for r in (ac.L1, ac.L2, ac.L3, ac.N)] == ["EL1", "EL2", "EL3", "EN"]
    assert [r.mark for r in (ac.L1, ac.L2, ac.L3, ac.N)] == [
        ConductorMark.L1,
        ConductorMark.L2,
        ConductorMark.L3,
        ConductorMark.N,
    ]
    assert [ac.L1.phase, ac.L2.phase, ac.L3.phase, ac.N.phase] == [0, 120, 240, None]
    assert set(_records(d, SupplySystem)[0].rails) == {"EL1", "EL2", "EL3", "EN"}


def test_ac_names_of_the_wrong_length_raise_with_the_expected_count(lib: Draft) -> None:
    d = design(lib, place="C1")
    pin = d.device("A1", "TEST-PSU-24V").out["+"]
    with pytest.raises(AuthorError, match=r"expected 4, not \('A', 'B', 'C'\)"):
        d.ac_supply("a", "230", pin, pin, pin, n=pin, names=("A", "B", "C"))
    with pytest.raises(AuthorError, match=r"expected 3"):
        d.ac_supply("b", "230", pin, pin, pin, names=("A", "B", "C", "D"))
    with pytest.raises(AuthorError, match=r"expected 2"):
        d.ac_supply("c", "230", pin, n=pin, names=("A",))
