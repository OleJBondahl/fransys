"""Field case: a signal pair through a cable joins X8:1 to B1:1 and X8:2 to B1:2, with no direction.

The engineering shape: a 2-wire sensor B1 and a terminal strip X8 are joined by the 3-core
cable W3. The sensor's signal function states no line or load side, and a CAN pair or a
current-sensor lead is the same. Core 1 runs pin 1 to pin 1, core 2 pin 2 to pin 2, so no core
flips between a line and a load end: `d.pair(x8[1:3], w3, b1.sig)`.

The need: `d.series` joins one element's load ends to the next one's line ends by pole, so it
refused the sideless function ("has no poles"), and `W3.core(1, ...)` by hand was the only way.

Decision (author-0058): `d.pair(a, cable, b)` reads no side; core i joins `a`'s pin i to
`b`'s pin i. The API rewrite keeps one verb for a pin-for-pin pair.
"""

from typing import TYPE_CHECKING

import fransys as fr

from fransys_model.vocab.tables import conductors, functions, ports
lazy from fransys_model.vocab import Port

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model


def _cores(model: Model, cable: str) -> dict[str, frozenset[str]]:
    """Core number -> the two ends as `X8:1` or `B1:2`."""
    fns = functions(model)

    def end(port_id: Id[Port]) -> str:
        port = ports(model)[port_id]
        key = fns[port.function].key
        return f"{key[0]}:{key[2] if key[1] == 'terminal' else port.name}"

    return {
        c.key[-1]: frozenset({end(c.a), end(c.b)})
        for c in conductors(model).values()
        if c.key[0] == cable
    }


def test_pair_joins_pin_for_pin() -> None:
    """Core 1 joins X8:1 to B1:1 and core 2 joins X8:2 to B1:2."""
    d = fr.design("demo_parts")
    x8 = d.terminal_strip("X8", "DEMO-TB-2.5")
    w3 = d.cable("W3", "DEMO-CBL-3X0.34")
    b1 = d.device("B1", "DEMO-SENSOR-2W")
    d.pair(x8[1:3], w3, b1.sig)
    assert _cores(fr.build(d).model, "W3") == {
        "1": frozenset({"X8:1", "B1:1"}),
        "2": frozenset({"X8:2", "B1:2"}),
    }


def test_pair_does_not_flip_on_a_sided_function() -> None:
    """A lamp with pin 1 on the line and pin 2 on the load side still goes pin for pin."""
    d = fr.design("demo_parts")
    x8 = d.terminal_strip("X8", "DEMO-TB-2.5")
    w3 = d.cable("W3", "DEMO-CBL-3X0.34")
    h1 = d.device("H1", "DEMO-LAMP-24")
    d.pair(x8[1:3], w3, h1.lamp)
    assert _cores(fr.build(d).model, "W3") == {
        "1": frozenset({"X8:1", "H1:1"}),
        "2": frozenset({"X8:2", "H1:2"}),
    }
