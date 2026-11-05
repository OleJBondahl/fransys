"""Field case: a terminal handle given where a port is meant, to a panel wire or a cable core.
The bug: such calls were accepted, then failed at build with a bare FreezeError naming no line of the author's code.
Fixed by the surface design: a terminal given to d.wire lands inner, and to W1.core lands outer."""

from typing import Any

import fransys as fr
from fransys.colours import BK

from fransys_model.vocab import Conductor, ConductorKind
from fransys_model.vocab.tables import conductors

_TERMINAL = "DEMO-TB-2.5"
_RELAY = "DEMO-CO-4P-24"
_CABLE = "DEMO-CBL-4G1.5"


def _ends(model: fr.Model, kind: ConductorKind) -> list[frozenset[Any]]:
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
    d.series(wired.inner, relay.co["12"], wire=(BK, 1.5))
    cable.core(1, cored, relay.co["11"])
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
    d.series(terminal.outer, relay.co["12"], wire=(BK, 1.5))
    (wire,) = _ends(fr.build(d).model, ConductorKind.WIRE)
    assert terminal.outer.id in wire
    assert terminal.inner.id not in wire
