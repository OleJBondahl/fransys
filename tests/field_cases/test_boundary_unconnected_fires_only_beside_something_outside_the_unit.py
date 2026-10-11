"""Field case: BOUNDARY_UNCONNECTED and the design that holds nothing but one unit.

The engineering shape: a unit hands back an eight-port switch as its interface, two ports wired
to a lamp inside, the rest open and not declared `unused=`. A consumer adds the unit as the
only thing in its design and sees no BOUNDARY_UNCONNECTED, where findings.md said the ERROR
fires for a non-standalone unit.

The rule, both ways: a unit is standalone when every item of the model belongs to its subtree
(`fransys_model.vocab.membership.standalone`). A standalone unit has no neighbour to mate, so
nothing is unconnected. One item outside it makes the unit non-standalone, and each of its nine
boundary functions (the supply and p1 to p8) fires: a wire inside the unit does not cross it.
The validator was right; the guide row said "top-level" and now says this.
"""

from typing import Any, NamedTuple

import fransys as fr


class _Io(NamedTuple):
    sw: Any


@fr.unit("demo-switch", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _switch(u: Any) -> _Io:
    sw = u.device("SW1", "DEMO-SW-8P", interface=True)
    lamp = u.device("H1", "DEMO-LAMP-24")
    u.wire(sw.p1["1"], lamp["1"], wire=("RD", 50))
    u.wire(sw.p2["1"], lamp["2"], wire=("BK", 50))
    return _Io(sw)


def _codes(*, outside: bool) -> list[str]:
    d = fr.design("demo_parts")
    d.add(_switch, "U1")
    if outside:
        d.device("H9", "DEMO-LAMP-24")
    return [f.code for f in fr.build(d).findings if f.code == "BOUNDARY_UNCONNECTED"]


def test_a_unit_alone_in_its_design_is_standalone_and_silent() -> None:
    assert _codes(outside=False) == []


def test_one_item_outside_the_unit_makes_its_open_ports_fire() -> None:
    assert _codes(outside=True) == ["BOUNDARY_UNCONNECTED"] * 9
