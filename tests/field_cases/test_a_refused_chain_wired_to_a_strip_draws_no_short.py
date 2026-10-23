"""Field case: a four-wire daisy chain of three modules, wired at both ends to a strip.

The engineering shape: three modules, each with a 4-in 4-out comms function. Each module's OUT
pins are wired to the next module's IN pins by four wires. The first module's IN pins 1 to 3
and the last module's OUT pin 3 are also wired to an external part-less strip.

The bug (v0.21.1): the chain is refused (CHAIN_REFUSED: a box is also wired by a net that is no
column attachment), and the boxes are then drawn unchained. That drawing is wrong: four risers
meet other nets (WIRE_MEETS_NET) and the build raises DRAWING_SHORTS_NETS ERROR, "a wire ends on
another with no junction dot". v0.20 drew it with no short. The correct behaviour: a refused
chain is drawn unchained and joins no nets.

Covered by: ROUTING and DRAWN-NETLIST (SHORTS-ROUTE R454) - layout core, trunk risers.
Decision: layout-0390 (a box pin of no net is a port end no wire passes).
"""

import sys
import tempfile
from itertools import pairwise
from pathlib import Path

import fransys as fr
from fransys.colours import BN, GN, WH, YE

sys.path.insert(0, str(Path(__file__).parent / "data"))  # the invented chain module part

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
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Chain\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


def test_a_refused_chain_drawn_unchained_has_no_drawing_shorts_nets() -> None:
    result = _built()
    assert [f.code for f in result.findings if f.code == "DRAWING_SHORTS_NETS"] == []
    assert any(f.code == "CHAIN_REFUSED" for f in result.findings)
