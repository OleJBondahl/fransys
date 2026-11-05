"""Field case: 11 clamp devices in one function block, each one's last 4 pins wired to the next one's first 4 by one 4-colour series.
The bug: the chain crosses a page break, and each cut net kept a drop to a trunk that has no line, so 8 wire ends dangle (ten devices are fine).
Fixed by order DANGLING-0223 (consumer N4): a page-cut two-pin net is wrapped by routing like a row-cut one, with no trunk."""

from itertools import pairwise

import fransys as fr
from _model_build_cover import unit_document
from fransys.colours import BN, GN, WH, YE

_COLOURS = ((GN, 0.5), (WH, 0.5), (BN, 0.5), (YE, 0.5))


def _findings(devices: int, links: int) -> set[str]:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("CHAIN", "Chain"):
        chain = [d.device(f"A{k}", "DEMO-IO-CLAMPS") for k in range(1, devices + 1)]
        for a, b in pairwise(chain):
            d.series(a.clamps.pins[8 - links :], b.clamps.pins[:links], wire=_COLOURS[:links])
    try:
        found = fr.build(d, unit_document(cab)).findings
    except fr.BuildFailedError as error:
        found = error.findings
    return {f.code for f in found}


def test_a_chain_of_four_conductor_links_across_a_page_break_has_no_dangling_end() -> None:
    assert "DANGLING_WIRE_END" not in _findings(11, 4)
