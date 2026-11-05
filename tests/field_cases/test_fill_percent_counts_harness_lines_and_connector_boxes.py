"""Field case: a cabinet page with two relay modules, each with a header, and a two-wire harness between two plugs mated to them.
The bug: fill_percent counted placed keep-outs, route vertices, labels and markers only, so harness lines and connector boxes did not count.
Fixed by layout-0194 (amends layout-0179), the share is the bounding box of everything drawn, including harness lines and connector boxes."""

import fransys as fr
from _model_build_cover import unit_document
from fransys.colours import BK, RD


def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    m1 = d.device("M1", "DEMO-RELAY-MOD-2")
    m2 = d.device("M2", "DEMO-RELAY-MOD-2")
    loom = d.harness("W1", place="C1")
    p1 = d.device("P1", "DEMO-HSG-4F", parent=loom, place="C1", contacts="DEMO-CRIMP-F")
    p2 = d.device("P2", "DEMO-HSG-4F", parent=loom, place="C1", contacts="DEMO-CRIMP-F")
    d.mate(p1, m1.j1)
    d.mate(p2, m2.j1)
    d.series(p1[1], p2[1], wire=(RD, 0.5))
    d.series(p1[2], p2[2], wire=(BK, 0.5))
    return fr.build(d, unit_document(cabinet))
