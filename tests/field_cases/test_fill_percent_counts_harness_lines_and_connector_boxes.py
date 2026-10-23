"""Field case: a page's fill share counts a harness line and its connector boxes.

The engineering shape: a cabinet page with two relay modules, each carrying a header, and a
loom W1 of two wires between two plugs, one plug mated to each header. The page draws two
plug boxes, two header boxes and one harness line.

The bug: `fill_percent` counted placed keep-outs, route vertices, labels and markers only, so
the boxes and the line did not count, and the page read as emptier than it is.
The rule: the share is the bounding box of everything drawn, so it covers harness lines,
fan-outs, connector boxes and black-box outlines too (amends layout-0179). Fixed by decision
layout-0194.
"""

from typing import TYPE_CHECKING

import fransys as fr
from fransys.colours import BK, RD


def _built(tmp_path_factory: pytest.TempPathFactory) -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    m1 = d.device("M1", "DEMO-RELAY-MOD-2")
    m2 = d.device("M2", "DEMO-RELAY-MOD-2")
    loom = d.harness("W1", place="C1")
    p1 = d.device("P1", "DEMO-HSG-4F", parent=loom, place="C1", contacts="DEMO-CRIMP-F")
    p2 = d.device("P2", "DEMO-HSG-4F", parent=loom, place="C1", contacts="DEMO-CRIMP-F")
    d.mate(p1, m1.j1)
    d.mate(p2, m2.j1)
    d.detail.wire(p1[1], p2[1], wire=(RD, 0.5))
    d.detail.wire(p1[2], p2[2], wire=(BK, 0.5))
    cover = tmp_path_factory.mktemp("cover") / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=cover))


if TYPE_CHECKING:
    import pytest
