"""Field case: a 2-pole DC switch, not an interface, with pole 1 in a chain fuse, contactor pole, terminal and pole 2 wired straight to a terminal.
The bug (v0.22.9): PLACEMENT_PROBLEM ERROR ("S1 ... has no pin") and CONNECTION_NOT_DRAWN 6; the symbol keeps pole 1's turn, pole 2's pin faces away.
Fixed under KI-751 (TWO-POLE-SWITCH-PIN); the second test is the KI-753 witness (SHARED-POLE-TURN, looks only), pole 2's cross-link."""

from typing import Any, NamedTuple

import fransys as fr
from _drawn_facts import symbol_subjects, wire_nets
from _model_build_cover import unit_document
from fransys.colours import BK, RD

_COLUMN = 16  # a wire inside one column: the pole spacing of the switch is its widest jog


class _Io(NamedTuple):
    """The interface strip."""

    X1: Any


@fr.unit("bars", revision=1, interface_version=1, date="2026-11-07", text="first", by="AB", title="Bars", number="N-1")
def _unit(u: Any) -> _Io:
    x1 = u.terminal_strip("X1", "DEMO-TB-2.5", 2, interface=True)
    s1 = u.device("S1", "DEMO-SWITCH-DC-2P")
    f1, k1 = u.device("F1", "DEMO-FUSE-DC-160"), u.device("K1", "DEMO-CONTACTOR-DC")
    u.series(s1.main.pole(1), f1.element, k1.pole, x1[1].inner, wire=(RD, 100))
    u.series(s1.main.pole(2), x1[2].inner, wire=(BK, 100))
    return _Io(x1)


def test_a_two_pole_switch_with_one_pole_in_a_chain_and_one_to_a_terminal_draws_every_connection() -> None:
    d = fr.design("demo_parts")
    d.add(_unit, "U1")
    found = fr.check(fr.build(d, unit_document("bars")))
    assert [f.code for f in found if f.severity.name == "ERROR"] == []
    assert [f for f in found if f.code == "CONNECTION_NOT_DRAWN"] == []


def test_the_terminal_of_the_second_pole_is_reached_inside_its_own_column() -> None:
    """The wires on terminal X1:2's x, the pin lead included, span no column: pole 2 needs no cross-link."""
    d = fr.design("demo_parts")
    d.add(_unit, "U1")
    model = fr.build(d, unit_document("bars")).model
    terminal = next(s for s in symbol_subjects(model) if s.tag == "U1-2")
    wires = [w for _, w in wire_nets(model) if any(x == terminal.x for x, _ in w.points)]
    xs = [x for w in wires for x, _ in w.points]
    assert max(xs) - min(xs) <= _COLUMN
