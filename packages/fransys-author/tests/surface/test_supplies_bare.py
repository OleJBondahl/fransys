"""EA15 G1 and G2: a DC supply with no source device, a mid rail, and one or three AC phases."""

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from fransys_author import AuthorError
from fransys_author.surface import design

from fransys_model.vocab import Net, SupplySystem

from .test_supplies import lib  # noqa: F401 -- the module fixture of the supply tests

if TYPE_CHECKING:
    from fransys_author.surface import Design

    from fransys_model.kernel import Draft


def _records(d: Design, cls: type) -> list:
    return [r for r in d.draft().records() if isinstance(r, cls)]


def _rails(d: Design) -> dict[str, Decimal]:
    (system,) = _records(d, SupplySystem)
    return {name: rail.max_v for name, rail in system.rails.items()}


def test_dc_supply_on_terminals_needs_no_source(lib: Draft) -> None:  # noqa: F811 -- fixture
    d = design(lib, place="C1")
    strip = d.terminal_strip("X1", "TEST-TERM")
    dc = d.dc_supply("feed", plus=strip[1], minus=strip[2], voltage=24)
    assert (dc.plus.pin, dc.minus.pin) == (strip[1].inner, strip[2].inner)
    assert (dc.plus.potential, dc.minus.potential) == ("24V", "0V")
    assert _rails(d) == {"24V": Decimal(24), "0V": Decimal(0)}
    assert {net.name for net in _records(d, Net)} == {"24V", "0V"}


def test_dc_supply_with_pins_and_no_source_names_the_missing_argument(lib: Draft) -> None:  # noqa: F811 -- fixture
    d = design(lib, place="C1")
    strip = d.terminal_strip("X1", "TEST-TERM")
    with pytest.raises(AuthorError, match=r"'feed' has no source, so it needs voltage="):
        d.dc_supply("feed", plus=strip[1], minus=strip[2])
    with pytest.raises(AuthorError, match=r"needs minus=, voltage="):
        d.dc_supply("feed", plus=strip[1])
    assert not _records(d, SupplySystem)


def test_a_given_voltage_overrides_the_source_nominal(lib: Draft) -> None:  # noqa: F811 -- fixture
    d = design(lib, place="C1")
    dc = d.dc_supply("psu", d.device("G1", "PSU-NOV").out, voltage="12")
    assert dc.plus.potential == "12V"


def test_mid_makes_minus_negative_and_mid_zero(lib: Draft) -> None:  # noqa: F811 -- fixture
    d = design(lib, place="C1")
    strip = d.terminal_strip("X1", "TEST-TERM")
    dc = d.dc_supply("pm", plus=strip[1], minus=strip[2], mid=strip[3], voltage=15)
    assert (dc.plus.potential, dc.minus.potential, dc.mid.potential) == ("15V", "-15V", "0V")
    assert _rails(d) == {"15V": Decimal(15), "-15V": Decimal(-15), "0V": Decimal(0)}


def test_free_names_and_two_zero_volt_rails_are_two_supplies(lib: Draft) -> None:  # noqa: F811 -- fixture
    d = design(lib, place="C1")
    strip = d.terminal_strip("X1", "TEST-TERM")
    d.dc_supply("a", plus=strip[1], minus=strip[2], voltage=24, names=("L+", "0V"))
    d.dc_supply("b", plus=strip[3], minus=strip[4], voltage=24, names=("24V", "GND"))
    assert {net.name for net in _records(d, Net)} == {"L+", "0V", "24V", "GND"}
    assert len(_records(d, SupplySystem)) == 2


def test_a_single_phase_is_l1_at_phase_zero(lib: Draft) -> None:  # noqa: F811 -- fixture
    d = design(lib, place="C1")
    strip = d.terminal_strip("X0", "TEST-TERM")
    ac = d.ac_supply("230V", 230, strip[1], n=strip[2])
    assert (ac.L1.pin, ac.N.pin) == (strip[1].inner, strip[2].inner)
    assert (ac.L1.phase, ac.L1.potential) == (0, "L1")
    assert _rails(d) == {"L1": Decimal(230), "N": Decimal(0)}
    with pytest.raises(AuthorError, match=r"no rail 'L2'; rails: L1, N"):
        _ = ac.L2


@pytest.mark.parametrize("count", [0, 2, 4])
def test_ac_supply_takes_one_or_three_phases(lib: Draft, count: int) -> None:  # noqa: F811 -- fixture
    d = design(lib, place="C1")
    pins = [d.device(f"A{i}", "TEST-PSU-24V").out["+"] for i in range(count)]
    with pytest.raises(AuthorError, match=rf"takes 1 or 3 phase pins, not {count}"):
        d.ac_supply("mains", "230", *pins)
    assert not _records(d, SupplySystem)
