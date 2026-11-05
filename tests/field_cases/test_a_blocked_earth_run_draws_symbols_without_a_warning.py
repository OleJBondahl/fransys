"""Field case: a protective-earth run a neighbouring pin blocks draws symbols and warns of nothing.
The bug: the refused run drew the earth symbols and a WARNING called it a Fransys defect with no user fix.
Fixed by layout-0190, a power run refused only because its straight wire is not free is drawn as power symbols with no finding."""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from _model_build_cover import unit_document
from fransys.colours import BU, GNYE

from fransys_model.layout import PowerSymbol, layout_of
from fransys_model.vocab.tables import functions, ports


class _Io(NamedTuple):
    LS: tuple[fr.Run, ...]
    PE: fr.Run
    PE_OUT: fr.Run


def _cabinet(phases: int, *, rail: bool) -> Any:
    @fr.unit("demo-cab", revision=1, interface_version=1, date="2026-10-14", text="first", by="AB")
    def cab(u: fr.Design) -> _Io:
        with u.function("SUP", "Supply"):
            x1 = u.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5", interface=True)
            ls = tuple(x1.run(f"L{k}", 1) for k in range(1, phases + 1))
            pe1 = x1.run("PE", 1)
            for k, run in enumerate(ls, 1):
                lamp = u.device(f"H{k}", "DEMO-LAMP-24")
                u.series(run[1].inner, lamp["1"], wire=(BU, 0.5))
                u.series(lamp["2"], pe1[1].inner, wire=(GNYE, 0.5))
        x3 = u.terminal_strip("X3", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5", interface=True)
        pe3 = x3.run("PE", 2, bridged=rail, rail=rail)
        outgoing = []
        for n in (1, 2):
            with u.function(f"P{n}", f"Pump {n}"):
                outgoing.append(pe3[n])
        for pe in outgoing:
            u.detail.busbar(pe1[1], pe)
        u.earth(pe1[1], *outgoing)
        return _Io(ls, pe1, pe3)

    return cab


def _build(phases: int, *, rail: bool = False) -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    d.project(title="PE", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-14", text="First issue", created="XX")
    cabinet = d.location("CAB", "Cabinet")
    cab = d.add(_cabinet(phases, rail=rail), "U1", place=None)
    with d.function("IN", "Incoming"):
        x0 = d.terminal_strip("X0", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5", external=True)
        for k, run in enumerate(cab.LS, 1):
            d.series(x0.run(f"L{k}", 1)[1].inner, run[1].outer, wire=(BU, 0.5))
        d.series(x0.run("PE", 1)[1].inner, cab.PE[1].outer, wire=(GNYE, 0.5))
    with d.function("OUT", "Outgoing"):
        x9 = d.terminal_strip("X9", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5", external=True)
        outs = x9.run("PE", 2)
        for n in (1, 2):
            d.series(cab.PE_OUT[n].outer, outs[n].inner, wire=(GNYE, 0.5))
    return fr.build(d, unit_document(cabinet), unit_document(cab))


def _earth_symbols(result: fr.BuildResult) -> int:
    return sum(s.symbol == "protective-earth" for s in layout_of(result.model, PowerSymbol).values())


def _earth_symbols_at(result: fr.BuildResult, strip: str) -> int:
    """The earth symbols standing on a port of the terminals of strip `strip`."""
    model = result.model
    count = 0
    for symbol in layout_of(model, PowerSymbol).values():
        item = functions(model)[ports(model)[symbol.port].function].item
        count += symbol.symbol == "protective-earth" and f"-{strip}:" in fr.derive.printed_designation(model, item)
    return count


@pytest.fixture(scope="module")
def blocked() -> fr.BuildResult:
    """The row earth, phase, earth, earth: the phase pin stands on the earth run's line."""
    return _build(phases=1)


@pytest.fixture(scope="module")
def free() -> fr.BuildResult:
    """The control: no phase terminal, and X3's PE strip is the declared rail (G08-POWER)."""
    return _build(phases=0, rail=True)


def test_a_flagged_pe_strip_draws_no_symbol_at_its_terminals_and_the_unflagged_ones_do(free: fr.BuildResult) -> None:
    """G08-POWER: the declared PE rail strip X3 draws no earth symbol; an unflagged terminal on the net draws its own."""
    assert _earth_symbols_at(free, "X3") == 0
    assert _earth_symbols_at(free, "X1") > 0


def test_a_blocked_earth_run_draws_its_symbols(
    blocked: fr.BuildResult,
) -> None:
    """The wire is refused, so each earth end takes its symbol, and nothing is left to fix."""
    assert _earth_symbols(blocked) > 0
