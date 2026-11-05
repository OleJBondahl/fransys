"""Field case: a four-wire daisy chain of three modules, wired at both ends to a strip.
The bug (v0.21.1): a refused chain was drawn unchained, its four risers met other nets, and the build raised DRAWING_SHORTS_NETS.
Fixed by layout-0390 (a box pin of no net is a port end no wire passes), a refused chain is drawn unchained and joins no nets."""

from itertools import pairwise

import fransys as fr
from _model_build_cover import unit_document
from fransys.colours import BN, GN, WH, YE

COMMS = ((GN, 0.5), (WH, 0.5), (BN, 0.5), (YE, 0.5))


def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", "intake_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    d.project(title="Chain", number="R-1", customer="Example Co", revision=1, author="XX")
    d.revision(1, date="2026-10-23", text="First issue", created="XX")
    with d.function("STRING", "Chain"):
        mods = [d.device(f"G{k}", "DEMO-MODULE-COM44") for k in (1, 2, 3)]
        for lower, upper in pairwise(mods):
            d.series(lower.comms.pins[4:], upper.comms.pins[:4], wire=COMMS)
    with d.function("JB", "Junction"):
        x2 = d.terminal_strip("X2", None, 4, external=True)
        d.series((x2[1].outer, x2[2].outer, x2[3].outer), mods[0].comms.pins[:3], wire=COMMS[:3])
        d.series(mods[-1].comms.COM_OUT_3, x2[4].outer, wire=COMMS[3])
    return fr.build(d, unit_document(cab))


def test_a_refused_chain_drawn_unchained_has_no_drawing_shorts_nets() -> None:
    result = _built()
    assert [f.code for f in result.findings if f.code == "DRAWING_SHORTS_NETS"] == []
    assert any(f.code == "CHAIN_REFUSED" for f in result.findings)
