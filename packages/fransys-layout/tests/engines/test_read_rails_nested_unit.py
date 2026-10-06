"""RB2 (model-0152): a wire from a sub-unit's pin to the parent unit's boundary rail terminal.

An end in sub-unit B of A lies inside A's subtree but in another unit, and every nested unit is
boundary-only on its parent, so the wire enters B's box: the parent's wire, kept, not a rail end.
"""

from typing import NamedTuple

import fransys as fr

from fransys_layout.engines.schematic.read import read_inputs


class _Pin(NamedTuple):
    pin: fr.Pin


@fr.unit("demo-sub-lamp", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _sub(u: fr.Design) -> _Pin:
    u.location("C1", "Cabinet")
    lamp = u.device("P1", "DEMO-LAMP-24")
    return _Pin(lamp.lamp["1"])


class _Io(NamedTuple):
    rail: tuple[fr.Terminal, ...]


@fr.unit("demo-rail-parent", revision=1, interface_version=1, date="2026-01-01", text="f", by="AB")
def _parent(u: fr.Design) -> _Io:
    u.location("C1", "Cabinet")
    psu = u.device("T1", "DEMO-PSU-24")
    x1 = u.terminal_strip("X1", "DEMO-TB-2.5", interface=True)
    plus = x1.run("24V", 2, bridged=True)
    dc = u.dc_supply("24V", plus=psu.output["+"], minus=psu.output["-"], voltage=24)
    u.wire(dc.plus.pin, plus[1], wire=("RD", 0.75))
    sub = u.add(_sub, "U2")
    u.wire(plus[2], sub.pin, wire=("RD", 0.75))
    return _Io((plus[1], plus[2]))


def test_a_wire_from_a_sub_unit_pin_to_the_parents_boundary_terminal_is_kept() -> None:
    d = fr.design("demo_parts", place="C1")
    d.add(_parent, "U1")
    inputs = read_inputs(fr.build(d).model)
    (lamp,) = (spec.function for spec in inputs.functions if spec.kind == "load")
    assert [c.a.function for c in inputs.connections] == [lamp]
    assert lamp not in {end.ref.function for end in inputs.rail_ends}
