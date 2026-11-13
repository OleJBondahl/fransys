"""Field case: a cable core from an external device ends on a strip terminal of a unit whose set fails layout; its wire is drawn on the project page.
The bug (KI-812, consumer 0.23.2): the project set reported CONNECTION_NOT_DRAWN for an end whose wire is drawn, because the far end's
home is the set that failed and its copy on this page was not read."""

from typing import Any, NamedTuple

import fransys as fr
from _expected_codes import expect_codes
from _model_build_cover import cabinet_document, unit_document


class _Io(NamedTuple):
    X1: Any


@fr.unit("crash-wide", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB", title="Crash wide", number="C-1")
def _unit(u: Any) -> _Io:
    with u.function("F1", "Monitoring"):
        monitor = u.device("B1", "FLD-GAS-MONITOR")
        controller = u.device("A1", "FLD-AI-CTRL-80")
    u.series(monitor.X1["1"], controller.ai_1["ANALOG_INPUT_01_P"], wire=("BK", 1.0))
    strip = u.terminal_strip("X1", "DEMO-TB-2.5", 1, interface=True)
    u.series(strip[1].inner, monitor.X1["2"], wire=("BK", 1.0))
    return _Io(X1=strip)


def _build() -> fr.BuildResult:
    d = fr.design("demo_parts", "crash_parts")
    unit = d.add(_unit, "U1")
    field = d.location("EXT", "External")
    ext = d.device("Q1", None, external=True, pins=("1", "2", "3"), place="EXT")
    w1 = d.cable("W1", "DEMO-CBL-3X0.34")
    d.series(ext["1"], w1, unit.X1[1].outer)
    w1.spare(2, 3)
    return fr.build(d, cabinet_document(field), unit_document(unit))


def test_an_external_device_cable_beside_a_failed_set_is_not_reported_undrawn() -> None:
    result = _build()
    expect_codes(result, "WIDER_THAN_PAGE", "PAGE_OVERFLOW")
    codes = {f.code for f in fr.check(result)}
    assert {"WIDER_THAN_PAGE", "PAGE_OVERFLOW"} <= codes
    assert "CONNECTION_NOT_DRAWN" not in codes
