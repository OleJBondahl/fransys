"""Field case GAP-FLIP-690 (KI-690): a sensor's supply pin on the unit's interface, open inside the unit, wired from the field by the carrier.
The bug: the unit built alone gave FUNCTION_HALF_CONNECTED and FUNCTION_NOT_WIRED on the open pin, and d.unused in the unit
then gave UNUSED_POINT_WIRED in the system build. Fixed by model-0426 (designer R1782)."""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from _expected_codes import expect_codes
from _model_build_cover import unit_document

_CODES = {"FUNCTION_HALF_CONNECTED", "FUNCTION_NOT_WIRED"}


class _Io(NamedTuple):
    h1: Any  # the sensor


@fr.unit("open-pin", revision=1, interface_version=1, date="2026-11-06", text="x", by="AB")
def _unit(u: Any) -> _Io:
    b7 = u.device("B7", "DEMO-PROX-PNP", interface=True)  # a 3-wire sensor on the Interface: supply pin 1 open, no d.unused
    u.series(b7.power["3"], b7.out["4"], wire=("BK", 0.75))
    return _Io(b7)


def _codes(result: fr.BuildResult) -> list[str]:
    return [f.code for f in result.findings if f.code in _CODES or f.code == "BOUNDARY_UNCONNECTED"]


def _built(*, wired: bool) -> fr.BuildResult:
    d = fr.design("demo_parts")
    unit = d.add(_unit, "U1")
    plug = d.device("P1", "DEMO-CONN-2P")  # the carrier's own device: the unit is no longer alone
    d.unused(unit.h1.out)  # the carrier leaves the sensor output to another carrier (R1761)
    if wired:
        d.cable("W1", "DEMO-CBL-4G1.5").core(1, plug[1], unit.h1["1"])
    return fr.build(d)


def _alone() -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_unit, "U1")
    return fr.build(d)


def test_the_unit_built_alone_takes_its_open_boundary_pin() -> None:
    assert _codes(_alone()) == []


def test_the_system_build_with_the_carrier_wiring_it_is_clean() -> None:
    assert _codes(_built(wired=True)) == []


def test_the_system_build_without_the_carriers_wire_still_reports() -> None:
    expect_codes(_built(wired=False), "FUNCTION_HALF_CONNECTED", "BOUNDARY_UNCONNECTED")


@fr.unit("idle-interface", revision=1, interface_version=1, date="2026-11-25", text="x", by="AB")
def _idle(u: Any) -> _Io:
    return _Io(u.device("X1", "DEMO-LAMP-24", interface=True))  # the whole interface device, no wire inside the unit


def test_a_wholly_unwired_interface_device_of_a_unit_alone_is_drawn_with_open_pins_and_no_finding() -> None:
    """KI-1519 (designer R3956): a boundary function is no loose function (model-0426), so NO-SILENT-DROP leaves it on the page."""
    d = fr.design("demo_parts")
    d.add(_idle, "U1")
    result = fr.build(d, unit_document("idle-interface"))
    assert [f.code for f in result.findings if f.code == "FUNCTION_NOT_WIRED"] == []
    assert [t.text for dr in result.drawings.values() for t in dr.texts] == ["-X1"]


@fr.unit("idle-strip", revision=1, interface_version=1, date="2026-11-25", text="x", by="AB")
def _strip(u: Any) -> _Io:
    return _Io(u.terminal_strip("X1", "DEMO-TB-2.5", 2, interface=(1, 2)))  # an interface strip no conductor reaches


@pytest.mark.rule("SPARE-TERMINALS")
def test_an_unwired_interface_strip_terminal_of_a_unit_alone_is_a_spare_terminal() -> None:
    """KI-1519 (designer R3966): an interface terminal no conductor reaches is spare: one INFO, no loose-function warning."""
    d = fr.design("demo_parts")
    d.add(_strip, "U1")
    findings = fr.build(d, unit_document("idle-strip")).findings
    assert [f.severity for f in findings if f.code == "SPARE_TERMINALS"] == [fr.Severity.INFO]
    assert [f.code for f in findings if f.code == "FUNCTION_NOT_WIRED"] == []
