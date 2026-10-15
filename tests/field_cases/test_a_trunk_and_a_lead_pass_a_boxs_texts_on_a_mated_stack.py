"""Field case: a connector box narrowed to its cells over a mated stack, a trunk and a lead by it.

The engineering shape: a contactor's lead housing `-K1-J10` is mated to a loom plug `-P18`, the
other plug `-P17` of that loom mates a four-pin header `-J7`, and each header pin runs to a lamp.
The drawing shows each connector as a box (its text, its pin cells), the loom as a line between.

The bug: the box was made as wide as its cells, so a lead's first run stood inside
the box and the lead's route ran back through the box's texts: WIRE_OVER_LABEL on the box and a
REDUNDANT_JOG on the lead. The fix (decision layout-0173): the router takes each box's rectangle
as a blocked shape and each pin faces away from it, with its marker, so a lead leaves its slot
away from the box and goes round it, and the markers stand at their pins.
"""

import tempfile
from functools import cache
from pathlib import Path

import fransys as fr
from fransys.colours import BK


@cache
def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    cab = d.location("C1", "Cabinet")
    j7 = d.device("J7", "DEMO-HSG-4F", contacts="DEMO-CRIMP-F")
    for n in range(1, 5):
        lamp = d.device(f"H{n}", "DEMO-LAMP-24")
        d.detail.wire(j7[n], lamp["1"], wire=(BK, 0.5))
    k1 = d.device("K1", "DEMO-CTR-LEADS")
    j10 = d.device(
        "J10",
        "DEMO-HSG-4F",
        parent=k1,
        contacts="DEMO-CRIMP-F",
        joins={"1": k1.coil["A1"], "2": k1.coil["A2"], "3": k1.aux["13"], "4": k1.aux["14"]},
    )
    d.detail.wire(k1.coil["A1"], d.device("H5", "DEMO-LAMP-24")["1"], wire=(BK, 0.5))
    d.detail.wire(k1.coil["A2"], d.device("H6", "DEMO-LAMP-24")["1"], wire=(BK, 0.5))
    w17 = d.harness("W17")
    pa = d.device("P17", "DEMO-HSG-4M", parent=w17, contacts="DEMO-CRIMP-M")
    pb = d.device("P18", "DEMO-HSG-4M", parent=w17, contacts="DEMO-CRIMP-M")
    d.mate(pa, j7)
    d.mate(pb, j10)
    for pin in (1, 2, 3, 4):
        d.detail.wire(pa[pin], pb[pin], wire=(BK, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


def test_no_route_or_line_runs_through_a_boxs_texts_and_none_makes_a_redundant_jog() -> None:
    bad = {"WIRE_OVER_LABEL", "WIRE_THROUGH_SYMBOL", "REDUNDANT_JOG"}
    assert [(f.code, f.message) for f in _built().findings if f.code in bad] == []
