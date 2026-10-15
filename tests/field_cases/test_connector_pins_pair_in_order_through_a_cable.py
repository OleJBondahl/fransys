"""Field case: two connectors with no line side pair their pins in order through a cable.

Engineering shape: a 4-pin header on a panel and a 4-pin header on a field box, joined by a
multi-core cable, pin 1 to pin 1 up to pin 4 to pin 4. A pin of a plain connector has no line
or load side, so there was nothing for `d.series` to pair by.

The bug: `d.series(j1.x1, w5, j2.x1, wire=...)` raised "has no poles: name its pins", so the
daisy chain of a harness was written pin by pin with `d.detail.wire`.

Fixing decision: author-0045 (two ends without a line side pair in pin order; a sideless
middle, a supply or rail end, unequal counts and equal names in different orders still raise).
"""

import fransys as fr
from fransys.colours import BK

from fransys_model.vocab import ConductorKind
from fransys_model.vocab.tables import conductors, ports


def _core_pins(d: fr.Design) -> list[tuple[str, str]]:
    """Each core's two pin names, in no order within a pair."""
    model = fr.build(d).model
    named = {pid: p.name for pid, p in ports(model).items()}
    return sorted(
        (named[c.a], named[c.b]) for c in conductors(model).values() if c.kind is ConductorKind.CORE
    )


def test_two_four_pin_connectors_pair_one_to_one_through_a_cable() -> None:
    d = fr.design("demo_parts", place="CAB")
    j1, j2 = d.device("J1", "DEMO-CONN-4P"), d.device("J2", "DEMO-CONN-4P")
    w5 = d.cable("W5", "DEMO-CBL-2X2X0.75-SP", length_m=3)
    d.series(j1.x1, w5, j2.x1, wire=(BK, 0.75))
    assert _core_pins(d) == [("1", "1"), ("2", "2"), ("3", "3"), ("4", "4")]
