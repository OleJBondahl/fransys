"""Field case: `d.parallel` of per-phase bridged runs ties L1, L2 and L3 together.
The bug: a series wires each member at full width, so every bridged run took all three poles and the phases were shorted, with no report.
Fixed by author-0015 (amended, PARALLEL-SHORTS), the series refuses at authoring time and names the spelling, one tap per phase."""

import fransys as fr
import pytest
from _field_designs import bridged_feeder
from fransys.colours import BK
from fransys_author import AuthorError

_START = "X1.run('L1') and X1.run('L2') both take poles L1, L2, L3:"


def test_three_bridged_runs_in_a_parallel_are_refused() -> None:
    d, ac, q0, x1 = bridged_feeder()
    runs = [x1.run(phase, bridged=True) for phase in ("L1", "L2", "L3")]
    with pytest.raises(AuthorError) as raised:
        d.series(ac, q0.element, d.parallel(*runs), wire=(BK, 2.5))
    assert str(raised.value).startswith(_START)


def test_one_bridged_run_per_phase_wired_pole_by_pole_builds() -> None:
    d, ac, q0, x1 = bridged_feeder()
    d.series(ac, q0.element, wire=(BK, 2.5))
    for pin, phase in (("2", "L1"), ("4", "L2"), ("6", "L3")):
        d.series(q0.element[pin], x1.run(phase, 3, bridged=True)[1], wire=(BK, 2.5))
    assert [f for f in fr.check(fr.build(d)) if f.severity is not fr.Severity.INFO] == []


def test_two_plain_runs_in_a_parallel_still_build() -> None:
    d, ac, q0, x1 = bridged_feeder()
    d.series(ac, q0.element, d.parallel(x1.run("A", 3), x1.run("B", 3)), wire=(BK, 2.5))
    assert [f for f in fr.check(fr.build(d)) if f.severity is not fr.Severity.INFO] == []


def test_the_refusal_names_a_tuple_of_taps_that_builds() -> None:
    d, ac, q0, x1 = bridged_feeder()
    runs = [x1.run(phase, bridged=True) for phase in ("L1", "L2", "L3")]
    with pytest.raises(AuthorError) as raised:
        d.series(ac, q0.element, d.parallel(*runs), wire=(BK, 2.5))
    assert "(X1.run('L1', n, bridged=True)[1], X1.run('L2', n, bridged=True)[1]" in str(raised.value)
    d, ac, q0, x1 = bridged_feeder()
    taps = tuple(x1.run(phase, 3, bridged=True)[1] for phase in ("L1", "L2", "L3"))
    d.series(ac, q0.element, taps, wire=(BK, 2.5))
    assert [f for f in fr.check(fr.build(d)) if f.severity is not fr.Severity.INFO] == []
