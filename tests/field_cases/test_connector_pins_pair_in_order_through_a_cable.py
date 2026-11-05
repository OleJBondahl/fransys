"""Field case: a 4-pin panel header and a 4-pin field box header, with no line side, joined by a multi-core cable.
The bug: d.series raised 'has no poles: name its pins' for the sideless pins, so the chain was wired pin by pin.
Fixed by author-0045, two ends without a line side pair in pin order; unequal counts and other mixes still raise."""

import fransys as fr
from fransys.colours import BK

from fransys_model.vocab import ConductorKind
from fransys_model.vocab.tables import conductors, ports


def _core_pins(d: fr.Design) -> list[tuple[str, str]]:
    """Each core's two pin names, in no order within a pair."""
    model = fr.build(d).model
    named = {pid: p.name for pid, p in ports(model).items()}
    return sorted((named[c.a], named[c.b]) for c in conductors(model).values() if c.kind is ConductorKind.CORE)


def test_two_four_pin_connectors_pair_one_to_one_through_a_cable() -> None:
    d = fr.design("demo_parts", place="CAB")
    j1, j2 = d.device("J1", "DEMO-CONN-4P"), d.device("J2", "DEMO-CONN-4P")
    w5 = d.cable("W5", "DEMO-CBL-2X2X0.75-SP", length_m=3)
    d.series(j1.x1, w5, j2.x1, wire=(BK, 0.75))
    assert _core_pins(d) == [("1", "1"), ("2", "2"), ("3", "3"), ("4", "4")]
