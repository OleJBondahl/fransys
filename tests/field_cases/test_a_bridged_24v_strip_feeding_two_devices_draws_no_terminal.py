"""Field case: a 24 V rail feeds a two-terminal strip, bridged, with each terminal feeding one device.
The bug: the placement engine drew both rail terminals, each with a power symbol, so the page showed terminals the rail already stands for.
Fixed by layout-0099 V3 (owner-backed 2026-10-02; designer R315), rails draw their power symbol and no rail terminal."""

import fransys as fr
from _drawn_pages import drawn_pages
from _model_build_cover import cabinet_document
from fransys.colours import BU

from fransys_model.derive import is_rail_terminal, terminal_rows, wire_rows
from fransys_model.derive.designation import port_designation
from fransys_model.layout import PowerSymbol, layout_of
from fransys_model.vocab.tables import items


def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Rail", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-19", text="First issue", created="XX")
    cab = d.location("CAB", "Cabinet")
    x10 = d.terminal_strip("X10", "DEMO-TB-2.5-TWIN", 2, bridged=True, rail=True)
    with d.function("G", "Group"):
        psu = d.device("T1", "DEMO-PSU-24")
        h1 = d.device("H1", "DEMO-LAMP-24")
        h2 = d.device("H2", "DEMO-LAMP-24")
    d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    d.dc_supply("S", psu)
    d.series(psu.output["+"], x10[1].inner, wire=(BU, 0.5))
    d.series(x10[1].inner, h1.lamp[1], wire=(BU, 0.5))
    d.series(x10[2].inner, h2.lamp[1], wire=(BU, 0.5))
    d.series(psu.output["-"], h1.lamp[2], wire=(BU, 0.5))
    d.series(psu.output["-"], h2.lamp[2], wire=(BU, 0.5))
    return fr.build(d, cabinet_document(cab))


def test_no_rail_terminal_is_drawn_and_each_device_pin_draws_the_rail_symbol() -> None:
    model = _built().model
    strip_items = {i.id for i in items(model).values() if i.tag == "X10"}
    rail = {i.id for i in items(model).values() if i.parent in strip_items}
    assert rail
    assert all(is_rail_terminal(model, i) for i in rail)
    keys = sorted(s.key for d in drawn_pages(model).values() for s in d.symbols)
    # the supply, two lamps and the power symbols the core places (el-0045); no terminal symbol
    # the two lamp returns (FUNCTION_HALF_CONNECTED) add two ground symbols to the supply's own: x1 became x3
    assert keys == ["generic-box", *["ground"] * 3, "lamp", "lamp", *["power-supply"] * 3]
    symbols = {port_designation(model, s.port) for s in layout_of(model, PowerSymbol).values() if s.symbol.startswith("power-supply")}
    assert {"-H1:1", "-H2:1", "-T1:+"} <= symbols
    assert not {p for p in symbols if p.startswith("-X10")}


def test_the_lists_keep_the_terminals_and_the_wires() -> None:
    model = _built().model
    (strip,) = (i.id for i in items(model).values() if i.tag == "X10")
    assert len(terminal_rows(model, strip)) == 2
    # three feed wires plus the two lamp returns to T1:-: 3 became 5
    assert len(wire_rows(model)) == 5
