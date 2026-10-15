"""Field case: a cable child with no landed connector is a fan-out end, not a plug.

The engineering shape: a harness W1 with a cable W2 and a mated plug P1 on a relay module. The
cable's one core runs from a pin of P1 to a terminal block T1 that is a child of the harness and
sits mated to a second relay module (a ferrule block: the core lands on a terminal function,
never on a connector).

The bug: the line text counted T1 as a fan-out end, but `block_diagram._is_plug` called any
non-cable child of a cable or harness a plug, so `end_box` took T1 through its mate to the
relay module. A plug needs a connector landed on it (model-0175); one `plug_of` fact decides it
for both readers, and the mate is the first `mate_partners` entry (model-0266, G4).
"""

import fransys as fr
import pytest

from fransys_model.derive import harness_line_ends
from fransys_model.derive.block_diagram import end_box
from fransys_model.derive.lookups import item_of_port
from fransys_model.vocab.tables import items, ports


@pytest.fixture(scope="module")
def model():
    d = fr.design("demo_parts")
    d.location("C1", "Cabinet")
    m1 = d.device("M1", "DEMO-RELAY-MOD-2", place="C1")
    m2 = d.device("M2", "DEMO-RELAY-MOD-2", place="C1")
    w1 = d.harness("W1", place="C1")
    p1 = d.device("P1", "DEMO-HSG-4F", parent=w1, place="C1", contacts="DEMO-CRIMP-F")
    d.mate(p1, m1.j1)
    cable = d.cable("W2", "DEMO-CBL-4G1.5", parent=w1, place="C1")
    t1 = d.device("T1", "DEMO-TB-2.5", parent=w1, place="C1")
    d.mate(t1, m2.j1)
    cable.core(1, p1[1], t1["external"])
    return fr.build(d).model


def _port_of(model, tag: str):
    item = next(i.id for i in items(model).values() if i.tag == tag)
    return next(p.id for p in ports(model).values() if item_of_port(model, p.id) == item)


def test_the_terminal_end_is_a_fan_out_end_on_the_line_and_the_diagram(model) -> None:
    """The line has one plug and one fan-out end; T1's port reaches no box through its mate."""
    harness = next(i.id for i in items(model).values() if i.tag == "W1")
    ends = harness_line_ends(model, harness)
    assert sorted(end.plug is None for end in ends) == [False, True]
    assert end_box(model, _port_of(model, "P1"), None) is not None
    assert end_box(model, _port_of(model, "T1"), None) is None


def test_a_plug_mated_twice_reaches_the_first_mate_in_designation_order() -> None:
    """G4: the mate is the first `mate_partners` entry, not the smallest item id (4 plugs)."""
    d = fr.design("demo_parts")
    d.location("C1", "Cabinet")
    w1 = d.harness("W1", place="C1")
    cable = d.cable("W2", "DEMO-CBL-4G1.5", parent=w1, place="C1")
    far = d.device("F1", "DEMO-HSG-4F", parent=w1, place="C1", contacts="DEMO-CRIMP-F")
    tags = []
    for n in range(1, 5):
        plug = d.device(f"P{n}", "DEMO-HSG-4F", parent=w1, place="C1", contacts="DEMO-CRIMP-F")
        low = d.device(f"A{n}", "DEMO-RELAY-MOD-2", place="C1")
        high = d.device(f"B{n}", "DEMO-RELAY-MOD-2", place="C1")
        d.mate(plug, high.j1)
        d.mate(plug, low.j1)
        cable.core(n, plug[1], far[n])
        tags.append((f"P{n}", f"A{n}"))
    model = fr.build(d).model
    assert len(tags) == 4
    for plug_tag, low_tag in tags:
        box = end_box(model, _port_of(model, plug_tag), None)
        assert box is not None
        landed = box.landed
        assert items(model)[landed].tag == low_tag
