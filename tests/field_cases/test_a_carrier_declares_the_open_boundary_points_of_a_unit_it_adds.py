"""Field case CARRIER-UNUSED: a released cabinet unit added into an outer design leaves boundary terminals open for another carrier.
The bug: BOUNDARY_UNCONNECTED fired, and `unused=` inside the unit put the carrier's fact into the unit.
Fixed by model-0481 (designer R1761, R1762): `d.unused(pc.x3[1], ...)` in the carrier."""

from typing import Any, NamedTuple
lazy from collections.abc import Iterable

import fransys as fr
import pytest
from _expected_codes import expect_codes
from fransys_author import AuthorError

_TB = "DEMO-TB-2.5"


class _Io(NamedTuple):
    x3: fr.TerminalStrip


@fr.unit("demo-cabinet", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _cabinet(d: fr.Design) -> _Io:
    return _Io(d.terminal_strip("X3", _TB, 4, interface=(1, 2, 3, 4)))


def _carrier(declare: Any = None) -> fr.BuildResult:
    d = fr.design("demo_parts")
    pc = d.add(_cabinet, "PC")
    h9 = d.device("H9", "DEMO-LAMP-24")  # outside the unit: the unit is not standalone
    d.series(pc.x3[1], h9["1"], wire=("RD", 2.5))
    d.series(pc.x3[2], h9["2"], wire=("BU", 2.5))
    if declare is not None:
        declare(d, pc)
    return fr.build(d)


def _codes(findings: Iterable[Any]) -> list[str]:
    return [f.code for f in findings]


def _checked(result: fr.BuildResult) -> list[str]:
    return _codes(fr.check(result))


def test_the_carrier_declares_its_open_points_quiet() -> None:
    control = _carrier()  # x3[3] and x3[4] fire
    expect_codes(control, "BOUNDARY_UNCONNECTED")
    assert "BOUNDARY_UNCONNECTED" in _checked(control)
    assert "BOUNDARY_UNCONNECTED" not in _checked(_carrier(lambda d, pc: d.unused(pc.x3[3], pc.x3[4])))


class _Few(NamedTuple):
    x3: fr.TerminalStrip


@fr.unit("demo-few", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _few(d: fr.Design) -> _Few:
    return _Few(d.terminal_strip("X3", _TB, 4, interface=(1, 2)))  # terminals 3 and 4 are inside the unit


def test_a_wired_point_listed_unused_is_refused() -> None:
    result = _carrier(lambda d, pc: d.unused(pc.x3[1], pc.x3[3], pc.x3[4]))
    expect_codes(result, "UNUSED_POINT_WIRED")
    codes = _checked(result)
    assert codes.count("UNUSED_POINT_WIRED") == 1
    assert "UNUSED_CONTRADICTED" not in codes  # the carrier's case has the one code


def test_a_point_that_is_no_boundary_is_refused() -> None:
    d = fr.design("demo_parts")
    pc = d.add(_few, "PC")
    h9 = d.device("H9", "DEMO-LAMP-24")
    d.series(pc.x3[1], h9["1"], wire=("RD", 2.5))
    d.series(pc.x3[2], h9["2"], wire=("BU", 2.5))
    assert "UNUSED_NOT_BOUNDARY" not in _checked(fr.build(d))
    d.unused(pc.x3[3])
    refused = fr.build(d)
    expect_codes(refused, "UNUSED_NOT_BOUNDARY")
    assert _checked(refused).count("UNUSED_NOT_BOUNDARY") == 1


def test_a_point_listed_twice_is_refused() -> None:
    with pytest.raises(AuthorError, match="UNUSED_LISTED_TWICE"):
        _carrier(lambda d, pc: d.unused(pc.x3[3], pc.x3[3]))


def _chain(declare: Any = None) -> fr.BuildResult:
    d = fr.design("demo_parts")
    m1, m2 = d.device("U1", "DEMO-MODULE-2P-COM4"), d.device("U2", "DEMO-MODULE-2P-COM4")
    d.series(m1.plus, m2.plus, wire=("RD", 1.5))
    if declare is not None:
        declare(d, m1, m2)
    return fr.build(d)


def test_a_port_declared_unused_is_no_half_connected_function() -> None:
    control = _chain()  # both minus ports are open
    expect_codes(control, "FUNCTION_HALF_CONNECTED")
    assert _checked(control).count("FUNCTION_HALF_CONNECTED") == 2
    one = _chain(lambda d, m1, _m2: d.unused(m1.minus))
    expect_codes(one, "FUNCTION_HALF_CONNECTED")
    assert _checked(one).count("FUNCTION_HALF_CONNECTED") == 1
    assert "FUNCTION_HALF_CONNECTED" not in _checked(_chain(lambda d, m1, m2: d.unused(m1.minus, m2.minus)))


def test_a_wired_port_listed_unused_is_refused() -> None:
    result = _chain(lambda d, m1, m2: d.unused(m1.plus, m1.minus, m2.minus))  # m2.minus declared: the one refusal is the wired port
    expect_codes(result, "UNUSED_POINT_WIRED")
    codes = _checked(result)
    assert codes.count("UNUSED_POINT_WIRED") == 1


def test_a_port_listed_twice_is_refused_naming_both_call_lines() -> None:
    with pytest.raises(AuthorError, match=r"UNUSED_LISTED_TWICE.*first at .*\.py:\d+, again at .*\.py:\d+"):
        _chain(lambda d, m1, _m2: d.unused(m1.minus, m1.minus))


def test_a_string_listed_unused_names_the_call_and_the_typed_spelling() -> None:
    with pytest.raises(AuthorError, match=r"d\.unused argument 1 is 'X3:3'.*no typed handle.*d\.unused\(pc\.x3\[3\]\)"):
        _carrier(lambda d, _pc: d.unused("X3:3"))
