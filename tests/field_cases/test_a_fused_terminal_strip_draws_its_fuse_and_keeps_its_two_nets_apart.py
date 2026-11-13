"""Field case: a bridged strip of fused terminals, 24 V on the internal sides, each external side feeding a lamp.
The bug: the terminal symbol drew both ports at one point, so the page joined 24 V to the fused outputs and hid the fuse.
Fixed by FUSE-TERMINAL (designer R2075): a protective link makes the table draw terminal-fuse."""

import fransys as fr
import pytest
from _drawn_pages import drawn_pages
from _expected_codes import expect_codes
from _model_build_cover import cabinet_document
from fransys.colours import BU

from electrical_symbols import LIBRARY
from fransys_layout.drawing import port_points


def _build(mpn: str) -> fr.BuildResult:
    d = fr.design("demo_parts", "fuse_parts", place="CAB")
    d.project(title="Fuse", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-11-09", text="First issue", created="XX")
    cab = d.location("CAB", "Cabinet")
    xf = d.terminal_strip("XF2", mpn, 2, bridged=True)
    with d.function("G", "Group"):
        psu = d.device("T1", "DEMO-PSU-24")
        h1 = d.device("H1", "DEMO-LAMP-24")
        h2 = d.device("H2", "DEMO-LAMP-24")
    d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    dc = d.dc_supply("24VDC", plus=psu.output["+"], minus=psu.output["-"], voltage=24, names=("24V", "GND"))
    d.series(dc.plus, xf[1], wire=(BU, 0.5))
    d.series(xf[1].outer, h1.lamp[1], wire=(BU, 0.5))
    d.series(xf[2].outer, h2.lamp[1], wire=(BU, 0.5))
    d.series(psu.output["-"], h1.lamp[2], wire=(BU, 0.5))
    d.series(psu.output["-"], h2.lamp[2], wire=(BU, 0.5))
    return fr.build(d, cabinet_document(cab))


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    return _build("FUSE-TB-2.5")


@pytest.mark.rule("FUSE-TERMINAL")
def test_each_fused_terminal_draws_its_fuse_between_two_unjoined_points(built: fr.BuildResult) -> None:
    drawn = [s for d in drawn_pages(built.model).values() for s in d.symbols if s.key.startswith("terminal")]
    assert len(drawn) == 2
    for symbol in drawn:
        assert symbol.key == "terminal-fuse"
        at = {pin: point for point, pin in port_points(symbol, LIBRARY)}
        assert at["n"] != at["s"]
        assert not any({"n", "s"} <= set(node.ports) for node in LIBRARY.symbols[symbol.key].nodes)
    assert [f.code for f in built.findings if f.severity is fr.Severity.ERROR] == []


def test_an_authored_symbol_that_draws_the_ports_of_a_protective_link_at_one_point_is_refused() -> None:
    result = _build("FUSE-TB-AUTHORED")
    expect_codes(result, "PLACEMENT_PROBLEM")
    errors = [f for f in result.findings if f.severity is fr.Severity.ERROR]
    assert [f.code for f in errors] == ["PLACEMENT_PROBLEM"]
    assert "a fused terminal part no longer names `symbol=`. Its protective link chooses the symbol. Delete the line" in errors[0].message
