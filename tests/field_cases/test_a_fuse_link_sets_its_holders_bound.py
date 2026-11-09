"""Field case: a fuse holder with a replaceable 4 A link feeds a 2 A switch on a branch of a 186 A source.
The bug: the holder stated no current, so its protection bounded nothing and the 2 A switch was never compared with 4 A.
Fixed by model-0151, the link is an accessory of the holder (parent=) and its rating bounds the holder's protection."""

from typing import Any

import fransys as fr
from _expected_codes import expect_codes

from fransys_model.derive import designation_list, item_designation

_BELOW_BRANCH = "RATING_CURRENT_BELOW_BRANCH"


def _build(*, switch: bool = True) -> tuple[fr.BuildResult, Any]:
    """G1 through the holder F1 (link 4 A) and, with `switch`, the 2 A switch S1 to two external terminals."""
    d = fr.design("demo_parts")
    g1 = d.device("G1", "DEMO-STRING-864V")
    f1 = d.device("F1", "DEMO-FUSE-HOLDER-PCB")
    link = d.device(None, "DEMO-FUSE-LINK-4A-T", name="link", parent=f1)
    s1 = d.device("S1", "DEMO-SWITCH-DC-2A") if switch else None
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 1, external=True)
    x2 = d.terminal_strip("X2", "DEMO-TB-2.5", 1, external=True)
    dc = d.dc_supply("HV", g1.string)
    d.series(dc.plus.pin, f1[1], wire=("BK", 1.5))
    d.series(f1[2], s1[1] if s1 else x1[1].inner, wire=("BK", 1.5))
    if s1:
        d.series(s1[2], x1[1].inner, wire=("BK", 1.5))
    d.series(dc.minus.pin, x2[1].inner, wire=("BK", 1.5))
    return fr.build(d), link


def test_the_link_prints_its_holders_designation_and_has_no_row() -> None:
    result, link = _build(switch=False)
    assert item_designation(result.model, link.id) == "F1"
    assert link.id not in {row.item for row in designation_list(result.model)}


def test_the_link_rated_4_a_bounds_the_branch_a_2_a_switch_sits_on() -> None:
    result, _ = _build()
    expect_codes(result, _BELOW_BRANCH)
    (finding,) = [f for f in fr.check(result) if f.code == _BELOW_BRANCH]
    assert finding.severity is fr.Severity.ERROR
    assert "branch's 4 A DC" in finding.message
    bounds = {b for c in fr.derive.current_chains(result.model) for p in c.positions for b in p.bounds}
    assert {(b.value, b.role.value) for b in bounds} == {(4, "protection")}
