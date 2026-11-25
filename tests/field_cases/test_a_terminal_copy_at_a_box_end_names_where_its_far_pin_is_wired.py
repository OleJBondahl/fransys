"""Field case: a strip terminal drawn at a box end is wired on another page at its other connection point.
KI-511: each placement names where its other copy is; a wired pin carries no marker (a drawn pin needs none).
The where-text under each placement's tag is the owner's reference text (R1202); the witness checks it with `where_joined` (R3741)."""

from typing import NamedTuple

import fransys as fr
import pytest
from _field_designs import fc_design
from _model_build_cover import unit_document
from fransys.colours import BU
from fransys_el import symbol_kit
from fransys_el.drawn_netlist import drawn_netlist
from fransys_el.drawn_where import where_joined

from electrical_symbols import LIBRARY
from fransys_model.derive import function_placements, port_function


class _Io(NamedTuple):
    L1: fr.Run
    N: fr.Run


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-10-14", text="first", by="AB")
def _cabinet(u: fr.Design) -> _Io:
    with u.function("SUP", "Supply"):
        x1 = u.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5", interface=True)
        l1, n = x1.run("L1", 1), x1.run("N", 1)
        lamp = u.device("H1", "DEMO-LAMP-24")
        u.series(l1[1].inner, lamp["1"], wire=(BU, 0.5))
        u.series(lamp["2"], n[1].inner, wire=(BU, 0.5))
    return _Io(l1, n)


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    d = fc_design("Stub", place="CAB")
    cabinet = d.location("CAB", "Cabinet")
    cab = d.add(_cabinet, "U1", place=None)
    with d.function("IN", "Incoming"):
        x0 = d.terminal_strip("X2", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5", external=True)
        cable = d.cable("W1", "DEMO-CBL-4G1.5", length_m=10)
        cable.core(1, x0.run("L1", 1)[1], cab.L1[1])
        cable.core(2, x0.run("N", 1)[1], cab.N[1])
    return fr.build(d, unit_document(cabinet), unit_document(cab))


def test_a_terminal_pin_wired_on_another_copy_has_reference_text_on_this_one(built: fr.BuildResult) -> None:
    """Each placement of a terminal that has another placement prints, under its tag, the where-text naming it (R1397)."""
    model = built.model
    net = drawn_netlist(model, symbol_kit(model, LIBRARY), built.drawings, (), LIBRARY)
    rows = function_placements(model)
    owed = {
        port
        for port, found in net.ids.items()
        if (function := port_function(model, found)) is not None and len({page for page, _ in rows.get(function, ())}) > 1
    }
    assert owed, "the build has no terminal with a second placement"
    assert owed <= where_joined(model, net), f"{len(owed - where_joined(model, net))} pin(s) of a multi-placement terminal print no where-text"
