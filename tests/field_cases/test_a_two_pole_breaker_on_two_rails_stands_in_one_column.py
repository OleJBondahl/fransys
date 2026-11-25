"""Field case: a 1P+N breaker with its phase pole on a fed rail and its neutral pole on another net stands in one column.
The bug: the control breaker's poles were dealt into two fans, so one symbol stood in two columns and was drawn twice.
Fixed by BUNDLE (R283), a through element takes its symbol's own column, and a symbol in two columns is a named error."""

import fransys as fr
from _drawn_pages import drawn_pages
from _model_build_cover import cabinet_document, error_messages
from fransys.colours import BK, BN, BU, GY

from electrical_symbols import LIBRARY
from fransys_layout.drawing import port_points

WIRE = 1.5


def _design() -> tuple[fr.Design, fr.Draft]:
    d = fr.design("demo_parts", "breaker_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    d.project(title="Rail", number="R-1", customer="Example Co", revision=1, author="XX")
    d.revision(1, date="2026-10-19", text="First issue", created="XX")
    with d.function("INC", "Incomer"):
        x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4, pe="DEMO-TB-PE-2.5")
        d.earth(x1.run("PE", 1)[1])
        d.ac_supply("400V", 230, x1[1], x1[2], x1[3], n=x1[4])
        q1 = d.device("Q1", "DEMO-ISO-4P")
        for terminal, pin, colour in ((1, "1", BN), (2, "3", BK), (3, "5", GY)):
            d.series(x1[terminal].inner, q1.main[pin], wire=(colour, 2.5))
        x01 = d.terminal_strip("X2", "DEMO-TB-2.5", 12)
        rails = [x01.run(name, 4, bridged=True) for name in ("L1", "L2", "L3")]
        for rail, pin, colour in zip(rails, ("2", "4", "6"), (BN, BK, GY), strict=True):
            d.series(q1.main[pin], rail[1].inner, wire=(colour, 2.5))
    with d.function("CTL", "Control supply"):
        f01, t1 = d.device("F1", "DEMO-MCB-1PN"), d.device("T1", "DEMO-PSU-24")
        d.series(rails[0][2].inner, f01.pole["1"], wire=(BN, WIRE))
        d.series(x1[4].inner, f01.pole["3"], wire=(BU, WIRE))
        d.series(f01.pole["2"], t1.input["L"], wire=(BN, WIRE))
        d.series(f01.pole["4"], t1.input["N"], wire=(BU, WIRE))
        d.dc_supply("24VDC", t1)
    with d.function("PUMPS", "Pumps"):
        for k in (1, 2):
            f, q = d.device(f"F{k}1", "DEMO-MCB-3P"), d.device(f"Q{k}1", "DEMO-CTR-3P-NC")
            xm = d.terminal_strip(f"XM{k}", "DEMO-TB-2.5", 3, pe="DEMO-TB-PE-2.5")
            for i, colour in enumerate((BN, BK, GY)):
                d.series(rails[i][2 + k].inner, f.element[("1", "3", "5")[i]], wire=(colour, WIRE))
                d.series(f.element[("2", "4", "6")[i]], q.main[("1", "3", "5")[i]], wire=(colour, WIRE))
                d.series(q.main[("2", "4", "6")[i]], xm[i + 1].inner, wire=(colour, WIRE))
    return d, cabinet_document(cab)


def test_the_build_has_no_error_finding() -> None:
    assert error_messages(fr.build(*_design())) == []


def _trafo_design() -> tuple[fr.Design, fr.Draft]:
    """A transformer whose secondary feeds a 2-pole breaker below it and a strip in another function."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    d.project(title="Rail", number="R-1", customer="Example Co", revision=1, author="XX")
    d.revision(1, date="2026-10-19", text="First issue", created="XX")
    with d.function("SUP", "Supply"):
        x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
        t1 = d.device("T1", "DEMO-TRAFO-400-230")
        d.series(x1[1].inner, t1.primary["1U"], wire=(BK, WIRE))
        d.series(x1[2].inner, t1.primary["1V"], wire=(BK, WIRE))
        f8 = d.device("F8", "DEMO-MCB-2P-C2")
        x2 = d.terminal_strip("X2", "DEMO-TB-2.5", 2)
        d.series((t1.secondary["2U"], t1.secondary["2V"]), f8.main, wire=(BK, WIRE))
        d.series(f8.main, (x2[1].inner, x2[2].inner), wire=(BK, WIRE))
    with d.function("OTH", "Other"):
        x3 = d.terminal_strip("X3", "DEMO-TB-2.5", 2)
        d.series((t1.secondary["2U"], t1.secondary["2V"]), (x3[1].inner, x3[2].inner), wire=(BK, WIRE))
    return d, cabinet_document(cab)


def test_a_breaker_fed_by_a_transformer_secondary_stands_plumb_under_its_first_pin() -> None:
    """VERTICAL-FIRST: the breaker's first pole stands in the secondary's first pin column (the second pole cannot: the pitches differ)."""
    result = fr.build(*_trafo_design())
    (page,) = drawn_pages(result.model).values()
    ports = {s.key: {n: at for at, n in port_points(s, LIBRARY)} for s in page.symbols if s.key in ("generic-box", "circuit-breaker")}
    assert ports["generic-box"]["secondary.2U"][0] == ports["circuit-breaker"]["1.in"][0]
