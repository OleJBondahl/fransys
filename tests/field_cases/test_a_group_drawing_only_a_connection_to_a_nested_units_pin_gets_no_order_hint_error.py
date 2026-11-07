"""Field case: a nested unit holds a DI module (in group PDI) and a switch (outside any group); group LSW holds only the series joining them.
The bug (v0.22.6): PLACEMENT_PROBLEM "hint names group 'LSW'". Fixed by model-0442: LSW draws nothing, so di_2 stays in PDI.
Consumer variants (module or series outside a group) gave CONNECTION_NOT_DRAWN; they do not reproduce here."""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from _expected_codes import expect_codes
from _model_build_cover import cabinet_document, unit_document
from fransys.colours import BU

from fransys_model.derive import function_moves
from fransys_model.kernel import Severity


class _Io(NamedTuple):
    DI1: Any
    S1: Any


@fr.unit("demo-di-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cab(d: Any) -> _Io:
    g1 = d.device("G1", "DEMO-PSU-24")
    dc = d.dc_supply("24VDC", g1.output)
    with d.function("PDI", "Inputs"):
        di1 = d.device("DI1", "DEMO-PLC-DI-2", interface=("di_2",))
    s1 = d.device("S1", "DEMO-LS-1NO1NC", interface=True)
    d.series(s1.no["14"], dc.minus, wire=(BU, 0.5))
    return _Io(di1, s1)


def build(*, series_in_group: bool = True) -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Hints", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-02", text="First issue", created="XX")
    cab = d.location("CAB", "Cabinet")
    u = d.add(_cab, "U1")
    if series_in_group:
        with d.function("LSW", "Level switch"):
            d.series(u.DI1.di_2, u.S1.no["13"], wire=(BU, 0.5))
    else:
        d.series(u.DI1.di_2, u.S1.no["13"], wire=(BU, 0.5))
    return fr.build(d, unit_document("demo-di-cab"), cabinet_document(cab))


@pytest.mark.rule("FUNCTION-BLOCK-DRAWS-ITS-WIRES")
def test_a_group_drawing_only_a_connection_to_a_nested_units_pin_gets_no_order_hint_error() -> None:
    result = build()
    codes = sorted(f.code for f in result.findings if f.severity is Severity.ERROR)
    assert codes == []
    assert not function_moves(result.model)
    expect_codes(result)
    assert "CONNECTION_NOT_DRAWN" not in {f.code for f in result.findings}
