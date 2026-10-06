"""model-0122, F1: a `protective` link (a fuse or breaker) ends the physical net, not the rail.

Built from `examples/demo-parts` only. A 24 V rail is declared on a fuse's input; the fuse's
output goes to a terminal of strip X01 (the valve supply). The strip side is on no physical net of
the rail (the fuse can open), yet it is in the rail closure (the fuse is closed in service).
"""

import fransys_parts
from fransys_author import Design

from fransys_model.derive import net_of, port_rails
from fransys_model.kernel import freeze, merge


def _model():
    d = Design(fransys_parts.load("demo_parts"))
    d.supply("24V", current="dc", rails={"+24V": ("24", None)})
    fuse = d.item("DEMO-MCB-C6", name="f1")
    strip = d.strip("X01")
    terminal = strip.terminal("DEMO-TB-2.5", "1")
    d.net("+24V", fuse["1"], cls="power", potential="+24V")
    d.wiring(colour="BK", gauge="1.5")(fuse["2"], terminal.inner)
    return freeze(merge(fransys_parts.load("demo_parts"), d.draft())), fuse, terminal


def test_the_strip_side_is_in_the_rail_closure_but_not_on_the_rails_physical_net() -> None:
    model, fuse, terminal = _model()
    rail_net = net_of(model, fuse["1"].id)
    assert rail_net is not None
    assert fuse["2"].id not in rail_net.ports
    assert terminal.inner.id not in rail_net.ports
    assert sorted(port_rails(model, terminal.inner.id)) == ["+24V"]
