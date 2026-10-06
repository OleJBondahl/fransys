"""Field case: a strip terminal given where a port is meant lands on the side the call defines.

The engineering shape: a terminal has two ports, the inner (panel-wiring) side and the outer
(field-cable) side. A panel wire and a cable core can each be given the terminal itself.

The bug (engine, old API): `wire(a, t)` and `cable.core(n, t, b)` with `t` a terminal handle were
accepted at the call, then failed at build with a bare `FreezeError` that named no line of the
author's code. The surface designs it out: a terminal handle is never ambiguous.

The rule (EA15, G8): a terminal given to `d.wire` lands on its inner side; given to `W1.core` it
lands on its outer side. `.outer` is also a valid `d.wire` end, and it lands on the outer side.
"""

import fransys as fr
from fransys.colours import BK

from fransys_model.vocab import Conductor, ConductorKind
from fransys_model.vocab.tables import conductors

_TERMINAL = "DEMO-TB-2.5"
_RELAY = "DEMO-CO-4P-24"
_CABLE = "DEMO-CBL-4G1.5"


def _ends(model: fr.Model, kind: ConductorKind) -> list[frozenset]:
    """The two port ids of each conductor of `kind`."""
    found: list[Conductor] = [c for c in conductors(model).values() if c.kind is kind]
    return [frozenset((c.a, c.b)) for c in found]


def _built() -> tuple[fr.Model, fr.Pin, fr.Pin, fr.Pin, fr.Pin]:
    """Terminals 1 and 2 of X01 and relay pins 12 and 11: the model and each terminal's sides."""
    d = fr.design("demo_parts", place="CAB")
    d.location("CAB", "Cabinet")
    strip = d.terminal_strip("X01", _TERMINAL)
    relay = d.device("K1", _RELAY)
    cable = d.cable("W1", _CABLE)
    wired, cored = strip[1], strip[2]
    d.wire(wired, relay.co_1["12"], wire=(BK, 1.5))
    cable.core(1, cored, relay.co_1["11"])
    model = fr.build(d).model
    return model, wired.inner, wired.outer, cored.inner, cored.outer


def test_wire_given_a_terminal_lands_on_its_inner_side() -> None:
    """If the wire landed on the outer side, its ends would hold the outer port, not the inner."""
    model, inner, outer, _, _ = _built()
    (wire,) = _ends(model, ConductorKind.WIRE)
    assert inner.id in wire
    assert outer.id not in wire


def test_cable_core_given_a_terminal_lands_on_its_outer_side() -> None:
    """If the core landed on the inner side, its ends would hold the inner port, not the outer."""
    model, _, _, inner, outer = _built()
    (core,) = _ends(model, ConductorKind.CORE)
    assert outer.id in core
    assert inner.id not in core


def test_outer_is_a_valid_wire_end() -> None:
    d = fr.design("demo_parts", place="CAB")
    d.location("CAB", "Cabinet")
    terminal = d.terminal_strip("X01", _TERMINAL)[1]
    relay = d.device("K1", _RELAY)
    d.wire(terminal.outer, relay.co_1["12"], wire=(BK, 1.5))
    (wire,) = _ends(fr.build(d).model, ConductorKind.WIRE)
    assert terminal.outer.id in wire
    assert terminal.inner.id not in wire
