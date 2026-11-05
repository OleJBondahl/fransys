"""Field case: a power supply's mains input is fed by a series from L1 through the supply to N.
The bug: the build raised "G1.input has no poles", because the demo part stated no sides on its two input pins.
Fixed by no decision record named; the rule: the demo part states `L` as the line side and `N` as the load side."""

import fransys as fr
from fransys.colours import BK


def test_a_series_from_l1_to_n_feeds_the_supply() -> None:
    """The series builds and `check` finds no error."""
    d = fr.design("demo_parts")
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5")
    ac = d.ac_supply("400V", "230", x0[1], x0[2], x0[3], n=x0[4])
    g1 = d.device("G1", "DEMO-PSU-24")
    d.series(ac.L1, g1.input, ac.N, wire=(BK, 2.5))
    assert not [f for f in fr.check(fr.build(d)) if f.severity.name == "ERROR"]
