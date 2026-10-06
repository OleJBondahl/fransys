"""Field case: a box device that also carries a connector draws, the connector as its own pin views.

The engineering shape: a redundancy module fed by two supplies (a box: two input groups, one
output) with a service connector, wired on pin 1 to a strip terminal.

The bug (BOX-CONTACT, layout-0123): the module's box-drawn functions form the box and the rest
draw apart, but the sides of the box's pins were still ranked over every drawn function of the
item. The connector's pin views, named by their port, reached the rank as a function that is
no function (KeyError), so the drawing could not be built.
The fix: the sides rank only the functions the box is made of (no decision, the rule is unchanged).
"""

import tempfile
from pathlib import Path

import fransys as fr
from fransys.colours import BN, BU

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs


def _layout():
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    live = d.terminal_strip("X1", "DEMO-TB-2.5", 2).run("L", 2, bridged=True)
    zero = d.terminal_strip("X2", "DEMO-TB-2.5", 2).run("L", 2, bridged=True)
    with d.function("G", "Group"):
        psus = [d.device(f"T{n}", "DEMO-PSU-24") for n in (1, 2)]
        m1 = d.device("M1", "DEMO-RED-2IN-NET")
    for n, psu in enumerate(psus, start=1):
        group = getattr(m1, f"in_{n}")
        d.wire(psu.output["+"], group[f"{n}+"], wire=(BN, 1.5))
        d.wire(psu.output["-"], group[f"{n}-"], wire=(BU, 1.5))
    d.dc_supply("S", plus=live[1], minus=zero[1], voltage=24)
    d.wire(m1.out["+"], live[1].outer, wire=(BN, 1.5))
    d.wire(m1.out["-"], zero[1].outer, wire=(BU, 1.5))
    d.wire(m1.svc["1"], live[2].outer, wire=(BN, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    model = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)).model
    return stage_results(model, read_inputs(model))[0].layout


def test_a_box_device_with_a_connector_is_drawn():
    layout = _layout()
    assert layout is not None
