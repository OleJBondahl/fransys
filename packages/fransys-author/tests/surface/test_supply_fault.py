"""RATINGS-3 R3: a supply states its fault current; a source's part does it for `source=`."""

from decimal import Decimal

import pytest
from fransys_author import AuthorError
from fransys_author.surface import design

from fransys_model.vocab import SupplySystem

from .test_supplies import lib  # noqa: F401 -- the module fixture of the supply tests


def _system(d) -> SupplySystem:
    (system,) = [r for r in d.draft().records() if isinstance(r, SupplySystem)]
    return system


def test_ac_supply_states_its_fault_current(lib) -> None:  # noqa: F811 -- fixture
    d = design(lib, place="C1")
    strip = d.terminal_strip("X1", "TEST-TERM")
    d.ac_supply("mains", 230, strip[1], fault_current_a="6000")
    assert _system(d).fault_current_a == Decimal(6000)
    assert _system(d).fault_time_constant_ms is None


def test_dc_supply_by_pins_states_both_values(lib) -> None:  # noqa: F811 -- fixture
    d = design(lib, place="C1")
    strip = d.terminal_strip("X1", "TEST-TERM")
    d.dc_supply(
        "bat",
        plus=strip[1],
        minus=strip[2],
        voltage=24,
        fault_current_a=Decimal(3000),
        fault_time_constant_ms=5,
    )
    assert (_system(d).fault_current_a, _system(d).fault_time_constant_ms) == (
        Decimal(3000),
        Decimal(5),
    )


def test_omitted_values_are_none(lib) -> None:  # noqa: F811 -- fixture
    d = design(lib, place="C1")
    strip = d.terminal_strip("X1", "TEST-TERM")
    d.dc_supply("bat", plus=strip[1], minus=strip[2], voltage=24)
    assert (_system(d).fault_current_a, _system(d).fault_time_constant_ms) == (None, None)


@pytest.mark.parametrize("keyword", ["fault_current_a", "fault_time_constant_ms"])
def test_a_source_with_either_keyword_raises(lib, keyword: str) -> None:  # noqa: F811 -- fixture
    d = design(lib, place="C1")
    source = d.device("G1", "PSU-NOV").out
    with pytest.raises(AuthorError, match=rf"dc_supply 'bat': drop {keyword}=; the source part"):
        d.dc_supply("bat", source, voltage=24, **{keyword: 100})  # ty: ignore[invalid-argument-type] -- a keyword by name
    assert d.dc_supply("bat", source, voltage=24).plus.potential == "24V"


@pytest.mark.parametrize("bad", [0, -5, "abc", "nan", 1.5, True])
def test_a_bad_value_raises(lib, bad: object) -> None:  # noqa: F811 -- fixture
    d = design(lib, place="C1")
    strip = d.terminal_strip("X1", "TEST-TERM")
    with pytest.raises(AuthorError, match="fault_current_a"):
        d.ac_supply("mains", 230, strip[1], fault_current_a=bad)  # ty: ignore[invalid-argument-type] -- the refusal under test
    with pytest.raises(AuthorError, match="fault_time_constant_ms"):
        d.dc_supply(
            "bat",
            plus=strip[2],
            minus=strip[3],
            voltage=24,
            fault_time_constant_ms=bad,  # ty: ignore[invalid-argument-type] -- the refusal under test
        )
