"""The kit draws every PLC channel, connector pin and pole group of the study instances (el-0014).

Each instance is rebuilt from its named test's builder and goes through `fransys_el.build`: it
returns, and the picks of each kind equal the view fact's rows. The skid of P7.2 is checked in
"""
# CONNECTION_NOT_DRAWN 10 per default-salt build set (MATES-DISABLED): mated, harness or board-unit input, refused for 0.22 (R1216).

from functools import cache
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest
from fransys_el.placement_kit import ProblemError
from fransys_el.symbol_pins import _pick, mating_face
from kit_instance_checks import built, check_channels, check_gangs, check_pins, laid_out
from kit_instances import INSTANCES

from electrical_symbols import LIBRARY

if TYPE_CHECKING:
    from fransys_el.placement_kit import SymbolKit

    from fransys_model.derive import PinView
    from fransys_model.kernel import Model


@cache
def _kit(name: str) -> tuple[Model, SymbolKit]:
    model = INSTANCES[name]()
    return model, built(model)


@pytest.mark.parametrize("name", INSTANCES)
def test_the_instance_builds_and_its_pin_picks_are_the_drawn_pin_rows(name: str) -> None:
    check_pins(*_kit(name))


@pytest.mark.parametrize("name", INSTANCES)
def test_every_plc_channel_is_a_pick_or_a_member_of_one(name: str) -> None:
    check_channels(*_kit(name))


@pytest.mark.parametrize("name", INSTANCES)
def test_the_gang_leads_hold_the_gang_members(name: str) -> None:
    check_gangs(*_kit(name))


@pytest.mark.parametrize("name", INSTANCES)
def test_the_instance_lays_out_with_pin_picks_in_its_scopes_and_tables(name: str) -> None:
    assert laid_out(*_kit(name)) > 0


def test_the_instances_between_them_hold_pins_and_channels() -> None:
    """The checks are not vacuous: the set holds connector pins, channels and one pin-free card."""
    pins = {name: check_pins(*_kit(name)) for name in INSTANCES}
    channels = {name: check_channels(*_kit(name)) for name in INSTANCES}
    assert pins["w06"] > 0
    assert pins["w09"] > 0
    assert channels["p02"] > 0
    assert channels["w03"] > 0


def test_a_connector_pin_binds_to_the_pin_port_and_never_to_the_mating_port() -> None:
    """`mate` is no pin: the symbol's pins are the port `pin` alone (CB-1 T3)."""
    view = cast("PinView", SimpleNamespace(name="A", port="p"))
    assert _pick(LIBRARY, view, ("pin-cell", frozendict({"A": "pin"}))).ports == {"p": "pin"}
    with pytest.raises(ProblemError):
        _pick(LIBRARY, view, ("pin-cell", frozendict({"A": "mate"})))


def test_each_pin_names_its_mating_port_when_the_symbol_has_one() -> None:
    """`mate` serves each pin, `<k>.mate` the pins `<k>.*`; a symbol with no mating port names none."""
    assert mating_face(["in", "out", "mate"]) == {"in": "mate", "out": "mate"}
    assert mating_face(["1.in", "1.mate", "2.in"]) == {"1.in": "1.mate"}
