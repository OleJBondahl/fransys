"""Field case: one bridged run as an element of a 3-pole series, meant as one terminal row for one phase.
The bug: the run took all three poles and its bridge shorted them, and the build reported nothing.
Fixed by author-0015 (amended, LONE-BRIDGE), the series refuses at authoring time and names the tuple spelling, one tap per phase."""

import fransys as fr
import pytest
from _field_designs import bridged_feeder
from fransys.colours import BK
from fransys_author import AuthorError

_START = "X1.run('L1') takes poles L1, L2, L3:"


def test_a_lone_bridged_run_in_a_three_pole_series_is_refused() -> None:
    d, ac, q0, x1 = bridged_feeder()
    with pytest.raises(AuthorError) as raised:
        d.series(ac, q0.element, x1.run("L1", bridged=True), wire=(BK, 2.5))
    assert str(raised.value).startswith(_START)
    assert "(X1.run('L1', n, bridged=True)[1], ...)" in str(raised.value)


def test_one_bridged_run_beside_a_plain_member_of_a_parallel_is_refused() -> None:
    d, ac, q0, x1 = bridged_feeder()
    plain = d.device("Q1", "DEMO-MCB-3P")
    with pytest.raises(AuthorError) as raised:
        d.series(ac, q0.element, d.parallel(x1.run("L1", bridged=True), plain.element), wire=(BK, 2.5))
    assert str(raised.value).startswith(_START)


def test_a_width_one_bridged_run_still_builds() -> None:
    d = fr.design("demo_parts")
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5", 2)
    dc = d.dc_supply("S", plus=x0[1], minus=x0[2], voltage=24)
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5")
    d.series(dc.plus, x1.run("P", 3, bridged=True, rail=True), wire=(BK, 1.5))
    assert [f for f in fr.check(fr.build(d)) if f.severity is not fr.Severity.INFO] == []
