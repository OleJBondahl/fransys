"""Fact 5: a rail pin stands a power symbol with no wire; a wire or a signal pin never does."""

from typing import TYPE_CHECKING

import fransys as fr
import pytest
from fransys.colours import BU, GNYE

from fransys_model.derive.stands import stands
from fransys_model.vocab import PowerKind
from fransys_model.vocab.tables import functions, items, ports

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Port

_WIRE = (BU, 0.5)


def _build() -> fr.BuildResult:
    """A 24 V PSU feeds three lamps; PE on lamps P4-P5; a wire P10-P11; a second PSU wired to P8."""
    d = fr.design("demo_parts")
    with d.function("G", "Group"):
        psu = d.device("T1", "DEMO-PSU-24")
        lamps = [d.device(f"P{i}", "DEMO-LAMP-24") for i in range(1, 4)]
        earthed = [d.device(f"P{i}", "DEMO-LAMP-24") for i in (4, 5)]
        signal = [d.device(f"P{i}", "DEMO-LAMP-24") for i in (10, 11)]
        psu2 = d.device("T2", "DEMO-PSU-24")
        lone = d.device("P8", "DEMO-LAMP-24")
    d.dc_supply("24VDC", psu, names=("P24", "P0"))
    for lamp in lamps:
        d.detail.wire(psu.output["+"], lamp[1], wire=_WIRE)
        d.detail.wire(psu.output["-"], lamp[2], wire=_WIRE)
    d.detail.wire(earthed[0][1], earthed[1][1], wire=(GNYE, 0.75))
    d.earth(earthed[0][1], earthed[1][1])
    d.detail.wire(signal[0][1], signal[1][1], wire=_WIRE)
    d.dc_supply("SOLO", psu2, names=("SOLO_24", "SOLO_0"))
    d.detail.wire(psu2.output["+"], lone[1], wire=_WIRE)
    d.detail.wire(psu2.output["-"], lone[2], wire=_WIRE)
    return fr.build(d)


@pytest.fixture(scope="module")
def model() -> Model:
    return _build().model


def _port(model: Model, tag: str, name: str) -> Id[Port]:
    """The port `name` of the device tagged `tag`."""
    (item,) = (i for i in items(model).values() if i.tag == tag)
    fns = {f.id for f in functions(model).values() if f.item == item.id}
    return next(p.id for p in ports(model).values() if p.function in fns and p.name == name)


def test_rail_pins_stand_their_power_kind(model: Model) -> None:
    result = stands(model)
    assert result[_port(model, "P1", "1")] is PowerKind.SUPPLY
    assert result[_port(model, "P3", "1")] is PowerKind.SUPPLY
    assert result[_port(model, "P1", "2")] is PowerKind.GROUND
    assert result[_port(model, "P5", "1")] is PowerKind.PE


def test_a_signal_pin_on_an_ordinary_net_stands_nothing(model: Model) -> None:
    result = stands(model)
    assert _port(model, "P10", "1") not in result
    assert _port(model, "P11", "1") not in result
    assert _port(model, "P1", "1") in result  # the rail pins of the same model do stand


def test_a_two_port_net_on_a_rail_potential_is_a_wire(model: Model) -> None:
    result = stands(model)
    assert _port(model, "P8", "1") not in result
    assert _port(model, "P8", "2") not in result
    assert _port(model, "P1", "1") in result  # the three-port rail pins of the first PSU stand
    assert _port(model, "P1", "2") in result
