"""Field case: a replaceable fuse link sets the current bound of the holder it sits in.

The engineering shape: a PCB fuse holder (two pads, a footprint, a voltage rating) carries a
replaceable link. The link is its own part with its own rated current: here 4 A, time-lag. A
small switch rated 2 A sits downstream of the holder on a branch of a 186 A source.

The bug: the holder states no current, so its protection function bounded nothing and the 2 A
switch was never compared with the 4 A the link lets through.

Fixing decision: model-0151 (the link is an accessory of the holder, `parent=`, and its rating
is one more source of the holder's protection function). The parts are `demo_parts`' invented ones.
"""

import fransys as fr

from fransys_model.derive import designation_list, item_designation

_BELOW_BRANCH = "RATING_CURRENT_BELOW_BRANCH"


def _build() -> tuple[fr.BuildResult, fr.Device]:
    """G1 through the holder F1 (link 4 A) and the 2 A switch S1 to two external terminals."""
    d = fr.design("demo_parts")
    g1 = d.device("G1", "DEMO-STRING-864V")
    f1 = d.device("F1", "DEMO-FUSE-HOLDER-PCB")
    link = d.device(None, "DEMO-FUSE-LINK-4A-T", name="link", parent=f1)
    s1 = d.device("S1", "DEMO-SWITCH-DC-2A")
    x1 = d.device("X1", "DEMO-TB-2.5", external=True)
    x2 = d.device("X2", "DEMO-TB-2.5", external=True)
    dc = d.dc_supply("HV", g1.string)
    d.wire(dc.plus.pin, f1[1], wire=("BK", 1.5))
    d.wire(f1[2], s1[1], wire=("BK", 1.5))
    d.wire(s1[2], x1["internal"], wire=("BK", 1.5))
    d.wire(dc.minus.pin, x2["internal"], wire=("BK", 1.5))
    return fr.build(d), link


def test_the_link_prints_its_holders_designation_and_has_no_row() -> None:
    result, link = _build()
    assert item_designation(result.model, link.id) == "F1"
    assert link.id not in {row.item for row in designation_list(result.model)}


def test_the_link_rated_4_a_bounds_the_branch_a_2_a_switch_sits_on() -> None:
    result, _ = _build()
    (finding,) = [f for f in fr.check(result) if f.code == _BELOW_BRANCH]
    assert finding.severity is fr.Severity.ERROR
    assert "branch's 4 A DC" in finding.message
    bounds = {
        b for c in fr.derive.current_chains(result.model) for p in c.positions for b in p.bounds
    }
    assert {(b.value, b.role.value) for b in bounds} == {(4, "protection")}
