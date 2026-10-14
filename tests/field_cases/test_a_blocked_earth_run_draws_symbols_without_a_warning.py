"""Field case: a protective-earth run a neighbouring pin blocks draws symbols and warns of nothing.

The engineering shape: a cabinet unit with two interface terminal strips. The first holds an
incoming phase terminal and a protective-earth terminal, the second two protective-earth terminals
for two outgoing circuits. The three earth terminals are bonded, and the unit is placed on the
system drawing, so its terminals stand in a row on the boundary page: earth, phase, earth, earth.

The bug (examples pump station, `JOIN_UNALIGNED` at the first PE terminal of -X1): the three earth
terminals are one run `join_y` can put on one line, but a straight wire between them would cross the
phase terminal's pin end, so the wire is refused. The refusal drew the earth symbols (the right
drawing) and also raised `JOIN_UNALIGNED`, a WARNING that calls a Fransys defect and leaves the
user nothing to fix.
The rule (decision layout-0190): a power run refused only because its straight wire is not free
is drawn as power symbols and gives no finding, as a run `place` cannot put on one line already
does. `JOIN_UNALIGNED` stays for a run `join_y` cannot align.
"""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from _model_build_cover import layout_trigger_document
from fransys.colours import BU, GNYE

from fransys_model.layout import PowerSymbol, layout_of


class _Io(NamedTuple):
    LS: tuple[fr.Run, ...]
    PE: fr.Run
    PE_OUT: fr.Run


def _cabinet(phases: int) -> Any:
    @fr.unit("demo-cab", revision=1, interface_version=1, date="2026-10-14", text="first", by="AB")
    def cab(u: fr.Design) -> _Io:
        with u.function("SUP", "Supply"):
            x1 = u.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5", interface=True)
            ls = tuple(x1.run(f"L{k}", 1) for k in range(1, phases + 1))
            pe1 = x1.run("PE", 1)
            for k, run in enumerate(ls, 1):
                u.wire(run[1], u.device(f"H{k}", "DEMO-LAMP-24")["1"], wire=(BU, 0.5))
        x3 = u.terminal_strip("X3", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5", interface=True)
        pe3 = x3.run("PE", 2)
        outgoing = []
        for n in (1, 2):
            with u.function(f"P{n}", f"Pump {n}"):
                outgoing.append(pe3[n])
        for pe in outgoing:
            u.rail_bond(pe1[1], pe)
        u.earth(pe1[1], *outgoing)
        return _Io(ls, pe1, pe3)

    return cab


def _build(phases: int) -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    d.project(title="PE", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-14", text="First issue", created="XX")
    d.location("CAB", "Cabinet")
    cab = d.add(_cabinet(phases), "U1", place=None)
    with d.function("IN", "Incoming"):
        x0 = d.terminal_strip("X0", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5", external=True)
        for k, run in enumerate(cab.LS, 1):
            d.wire(x0.run(f"L{k}", 1)[1], run[1], wire=(BU, 0.5))
        d.wire(x0.run("PE", 1)[1], cab.PE[1], wire=(GNYE, 0.5))
    with d.function("OUT", "Outgoing"):
        x9 = d.terminal_strip("X9", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5", external=True)
        outs = x9.run("PE", 2)
        for n in (1, 2):
            d.wire(cab.PE_OUT[n], outs[n], wire=(GNYE, 0.5))
    return fr.build(d, layout_trigger_document())


def _unaligned(result: fr.BuildResult) -> list[fr.Finding]:
    return [f for f in fr.check(result) if f.code == "JOIN_UNALIGNED"]


def _earth_symbols(result: fr.BuildResult) -> int:
    return sum(
        s.symbol == "protective-earth" for s in layout_of(result.model, PowerSymbol).values()
    )


@pytest.fixture(scope="module")
def blocked() -> fr.BuildResult:
    """The row earth, phase, earth, earth: the phase pin stands on the earth run's line."""
    return _build(phases=1)


@pytest.fixture(scope="module")
def free() -> fr.BuildResult:
    """The control: no phase terminal, so the earth run's wire is free."""
    return _build(phases=0)


def test_an_earth_run_with_a_free_wire_is_one_wire_and_no_symbol(free: fr.BuildResult) -> None:
    """The control: the run is wired, so the unit's boundary page draws no earth symbol."""
    assert _unaligned(free) == []
    assert _earth_symbols(free) == 0


def test_a_blocked_earth_run_draws_its_symbols_and_gives_no_join_unaligned(
    blocked: fr.BuildResult,
) -> None:
    """The wire is refused, so each earth end takes its symbol, and nothing is left to fix."""
    assert _earth_symbols(blocked) > 0
    assert _unaligned(blocked) == []
