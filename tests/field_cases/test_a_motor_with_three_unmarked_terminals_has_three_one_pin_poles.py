"""Field case: a three-phase motor's terminals U, V and W are three one-pin poles.

The engineering shape: a load whose part file names three terminals and no pole link, none with a
line or load side. The terminals are not two ends of one path.

The bug: `poles_of` fell back on `unlinked_poles`, which pairs consecutive pins, so U and V formed
one pole and W stood alone as (W, W). The pairing is the rule for a pass-through function, whose
pins come as line and load ends.
The fix: NS-2b, designer 2026-10-18 Ruling 16 item 3: a function whose pins have no line/load
side gets one one-pin pole per pin.
"""

import fransys as fr
import pytest
from fransys.colours import BU

from fransys_model.derive.pole_lists import poles_of
from fransys_model.vocab.tables import functions, port_templates, ports


@pytest.fixture(scope="module")
def built() -> fr.Model:
    """One design: the demo motor M1 with U, V and W wired to demo connectors."""
    d = fr.design("demo_parts")
    d.location("L0", "Workshop")
    with d.function("DRV", "Drive"):
        m = d.device("M1", "DEMO-MOTOR-4KW", place="L0")
        for pin, far in (("U", "J1"), ("V", "J2"), ("W", "J3")):
            d.detail.wire(m[pin], d.device(far, "DEMO-CONN-2P", place="L0")[1], wire=(BU, 0.5))
    return fr.build(d).model


def test_the_poles_are_u_v_and_w_alone(built: fr.Model) -> None:
    (motor,) = [f for f in functions(built).values() if f.name == "motor"]
    own = [p.template for p in ports(built).values() if p.function == motor.id and p.template]
    poles = [
        tuple(port_templates(built)[t.id].name for t in pole.ends) for pole in poles_of(built, own)
    ]
    assert poles == [("U", "U"), ("V", "V"), ("W", "W")]
