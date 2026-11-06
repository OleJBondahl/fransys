"""Field case: d.earth from a motor's PE pin to a PE strip terminal draws the terminal and does not list it as a spare.
The bug: the terminal's two sides were one two-port net, read as a wire, so no PE symbol stood on it and SPARE_TERMINALS listed it.
Fixed by KI-704 (R1798): a terminal's two sides on a PE net are no wire, so it stands on the PE net like a wired one (only PE: KI-708)."""

from typing import NamedTuple

import fransys as fr
import pytest
from _model_build_cover import unit_document
from fransys.colours import RD

from fransys_model.layout import PowerSymbol, layout_of


class _Io(NamedTuple):
    X1: fr.TerminalStrip


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-11-06", text="first", by="AB")
def _cab(u: fr.Design) -> _Io:
    x1 = u.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5")
    pe = x1.run("PE", 1)
    m1 = u.device("M1", "DEMO-MOTOR-4KW")
    u.earth(m1.motor["PE"], pe[1])
    return _Io(x1)


@fr.unit("demo-rail", revision=1, interface_version=1, date="2026-11-06", text="first", by="AB")
def _rail(u: fr.Design) -> _Io:
    x2 = u.terminal_strip("X2", "DEMO-TB-FUSE-2.5", 4, bridged=True)
    psu = u.device("G1", "DEMO-PSU-24")
    dc = u.dc_supply("24VDC", plus=psu.output["+"], minus=psu.output["-"], voltage=24, names=("24V", "GND"))
    u.series(dc.plus, x2[1], wire=(RD, 2.5))
    return _Io(x2)


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    d.project(title="PE", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-11-06", text="First issue", created="XX")
    d.location("CAB", "Cabinet")
    return fr.build(d, unit_document(d.add(_cab, "U1", place=None)))


def _earthed(result: fr.BuildResult) -> list[str]:
    model = result.model
    symbols = layout_of(model, PowerSymbol).values()
    return [fr.derive.port_designation(model, s.port) for s in symbols if s.symbol == "protective-earth"]


def test_the_terminal_stands_on_the_pe_net_with_the_motor(built: fr.BuildResult) -> None:
    on_pe = _earthed(built)
    assert "-U1-M1:PE" in on_pe
    assert "-U1-X1:PE:1" in on_pe


def test_the_terminal_is_not_a_spare(built: fr.BuildResult) -> None:
    spare = [f for f in built.findings if f.code == "SPARE_TERMINALS"]
    assert spare == []


def test_an_unwired_terminal_of_a_bridged_unflagged_strip_on_24v_stays_a_spare() -> None:
    d = fr.design("demo_parts", place="CAB")
    d.project(title="PE", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-11-06", text="First issue", created="XX")
    d.location("CAB", "Cabinet")
    result = fr.build(d, unit_document(d.add(_rail, "U1", place=None)))
    spare = [f for f in result.findings if f.code == "SPARE_TERMINALS"]
    assert spare, [f.code for f in result.findings]
