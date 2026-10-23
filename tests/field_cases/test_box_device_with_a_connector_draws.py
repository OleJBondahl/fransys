"""Field case: a box device that also carries a connector draws, the connector as its own pin views.

The engineering shape: a redundancy module fed by two supplies (a box: two input groups, one
output) with a service connector, wired on pin 1 to a strip terminal.

The bug (layout-0123): the module's box-drawn functions form the box and the rest
draw apart, but the sides of the box's pins were still ranked over every drawn function of the
item. The connector's pin views, named by their port, reached the rank as a function that is
no function (KeyError), so the drawing could not be built.
The fix: the sides rank only the functions the box is made of (no decision, the rule is unchanged).
"""

import tempfile
from pathlib import Path

import fransys as fr
import pytest
from _drawn_pages import drawn_pages
from fransys.colours import BN, BU


def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    live = d.terminal_strip("X1", "DEMO-TB-2.5", 2).run("L", 2, bridged=True)
    zero = d.terminal_strip("X2", "DEMO-TB-2.5", 2).run("L", 2, bridged=True)
    with d.function("G", "Group"):
        psus = [d.device(f"T{n}", "DEMO-PSU-24") for n in (1, 2)]
        m1 = d.device("M1", "DEMO-RED-2IN-NET")
    for n, psu in enumerate(psus, start=1):
        group = getattr(m1, f"in_{n}")
        d.detail.wire(psu.output["+"], group[f"{n}+"], wire=(BN, 1.5))
        d.detail.wire(psu.output["-"], group[f"{n}-"], wire=(BU, 1.5))
    d.dc_supply("S", plus=live[1], minus=zero[1], voltage=24)
    d.detail.wire(m1.out["+"], live[1].outer, wire=(BN, 1.5))
    d.detail.wire(m1.out["-"], zero[1].outer, wire=(BU, 1.5))
    d.detail.wire(m1.svc["1"], live[2].outer, wire=(BN, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


def test_a_box_device_with_a_connector_is_drawn():
    symbols = [one for drawing in drawn_pages(_built().model).values() for one in drawing.symbols]
    assert any(one.key == "generic-box" for one in symbols), "the module's box is drawn"


@pytest.mark.rule("SERIES-PARALLEL")
def test_the_two_supplies_stand_side_by_side_above_the_module() -> None:
    """Series(Parallel(T1, T2), M1): one column, no CHAIN_REFUSED (it was refused before P2)."""
    built = _built()
    assert "CHAIN_REFUSED" not in {f.code for f in built.findings}
    boxes = [s for d in drawn_pages(built.model).values() for s in d.symbols]
    tops = [s.y for s in boxes if s.key == "generic-box"]
    assert len(tops) == 3
    assert tops.count(min(tops)) == 2, "the two supplies stand on one row"
    assert max(tops) > min(tops), "the module stands below them"
