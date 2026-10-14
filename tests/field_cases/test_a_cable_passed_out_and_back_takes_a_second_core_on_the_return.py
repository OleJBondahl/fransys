"""Field case: one cable passed out to a field lamp and back lands its return on core 2.

The engineering shape: a 24 V supply feeds a field lamp H1 through a terminal strip X1 and the
4-core cable W1, and the return runs back through the same cable and strip:
`d.series(dc.plus, x1, w1, h1.lamp, w1, x1, dc.minus)`.

The bug: both passes took core 1, so the build raised "W1 core 1 is already wired or marked spare".

Rule (author-0041): each pass of a cable takes its next free core, so the return leg takes core 2.
"""

import fransys as fr
from fransys.colours import BU

from fransys_model.vocab.tables import conductors, items


def test_the_return_leg_takes_the_second_core() -> None:
    """The series builds, and W1 carries cores 1 and 2 as two conductors on the cable."""
    d = fr.design("demo_parts")
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24").output)
    d.location("FIELD", "Field")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5")
    w1 = d.cable("W1", "DEMO-CBL-4G1.5", length_m=12)
    h1 = d.device("H1", "DEMO-LAMP-24", place="FIELD")
    d.series(dc.plus, x1, w1, h1.lamp, w1, x1, dc.minus, wire=(BU, 0.75))
    result = fr.build(d)
    assert not [f for f in fr.check(result) if f.severity.name == "ERROR"]
    (w1_id,) = [i.id for i in items(result.model).values() if i.tag == "W1"]
    cores = [c for c in conductors(result.model).values() if c.carrier == w1_id]
    assert len(cores) == 2
