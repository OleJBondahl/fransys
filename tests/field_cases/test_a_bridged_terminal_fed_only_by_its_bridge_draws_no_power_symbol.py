"""Field case: an unflagged bridged fuse strip is fed on terminal 1 by a DC supply's plus pole; terminal 2 carries a branch.
The bug: terminal 2, reached on its feed side only by the bridge, drew the net's power symbol, though a bridge shows in the terminal table only.
Fixed by BRIDGED-SYMBOL (owner 2026-11-21: a power symbol stands for a declared rail): the revert BRIDGE-POTENTIAL-REVERT stands."""

import fransys as fr
from _drawn_pages import drawn_pages
from _field_designs import fc_design
from _model_build_cover import cabinet_document
from fransys.colours import BU

from fransys_model.derive.designation import port_designation
from fransys_model.layout import PowerSymbol, layout_of


def _built() -> fr.BuildResult:
    d = fc_design("Fused", place="CAB", date="2026-11-24")
    cab = d.location("CAB", "Cabinet")
    xf = d.terminal_strip("XF", "DEMO-TB-FUSE-2.5", 2, bridged=True)
    xg = d.terminal_strip("XG", "DEMO-TB-2.5", 2)
    with d.function("G", "Group"):
        psu = d.device("T1", "DEMO-PSU-24")
    d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    dc = d.dc_supply("S", psu)
    d.series(dc.plus, xf[1], wire=(BU, 0.5))
    d.series(xf[2].outer, xg[2].inner, wire=(BU, 0.5))
    d.series(dc.minus, xg[1], wire=(BU, 0.5))
    return fr.build(d, cabinet_document(cab))


def test_no_power_symbol_stands_at_a_terminal_only_a_bridge_feeds() -> None:
    model = _built().model
    symbols = [port_designation(model, s.port) for s in layout_of(model, PowerSymbol).values()]
    assert not [p for p in symbols if p.startswith("-XF")]
    assert "-XG:1" in symbols  # the declared 0 V side keeps its ground symbol


def test_the_unflagged_strip_draws_two_terminals_and_no_power_symbol_on_the_page() -> None:
    model = _built().model
    keys = [s.key for d in drawn_pages(model).values() for s in d.symbols]
    assert keys.count("terminal-fuse") == 2
    assert "power-supply" not in keys
