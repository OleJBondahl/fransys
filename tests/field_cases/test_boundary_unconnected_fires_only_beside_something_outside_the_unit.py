"""Field case: BOUNDARY_UNCONNECTED and the design that holds nothing but one unit.
The bug: none in the validator, which was right; the guide row said top-level, so a lone unit was expected to fire.
Fixed by the rule, no record named: a unit is standalone when every item lies in its subtree, and the guide says so."""

from typing import Any, NamedTuple

import fransys as fr
from _expected_codes import expect_codes


class _Io(NamedTuple):
    sw: Any


@fr.unit("demo-switch", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _switch(u: Any) -> _Io:
    sw = u.device("SW1", "DEMO-SW-8P", interface=True)
    lamp = u.device("H1", "DEMO-LAMP-24")
    u.series(sw.p1["1"], lamp["1"], wire=("RD", 50))
    u.series(sw.p2["1"], lamp["2"], wire=("BK", 50))
    return _Io(sw)


def _build(*, outside: bool) -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_switch, "U1")
    if outside:
        d.device("H9", "DEMO-LAMP-24")
    return fr.build(d)


def _open(result: fr.BuildResult) -> list[str]:
    return [f.code for f in result.findings if f.code == "BOUNDARY_UNCONNECTED"]


def test_a_unit_alone_in_its_design_is_standalone_and_silent() -> None:
    assert _open(_build(outside=False)) == []


def test_one_item_outside_the_unit_makes_its_open_ports_fire() -> None:
    result = _build(outside=True)
    expect_codes(result, "BOUNDARY_UNCONNECTED")
    assert len(_open(result)) == 9
