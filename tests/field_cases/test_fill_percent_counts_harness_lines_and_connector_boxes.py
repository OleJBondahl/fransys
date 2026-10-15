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

from decimal import Decimal

import fransys as fr
import pytest
from fransys.colours import BK, RD
from fransys_el import OPTIONS

from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.stages.content import content_box
from fransys_model.layout import ConnectorBox, HarnessLine, SymbolPlacement, layout_of


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


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> fr.BuildResult:
    return _built(tmp_path_factory)


def test_the_share_covers_the_boxes_and_the_line(built: fr.BuildResult) -> None:
    """The page reads at least the share of the box around every drawn point it holds."""
    model = built.model
    boxes = layout_of(model, ConnectorBox).values()
    (line,) = layout_of(model, HarnessLine).values()
    xs = [x for one in boxes for x in (one.x, one.x + one.width)]
    ys = [y for one in boxes for y in (one.y, one.y + one.height)]
    xs += [p.x for p in line.points] + [one.x for one in layout_of(model, SymbolPlacement).values()]
    ys += [p.y for p in line.points] + [one.y for one in layout_of(model, SymbolPlacement).values()]
    content = content_box(read_inputs(model, options=OPTIONS).sheet)
    least = Decimal((max(xs) - min(xs)) * (max(ys) - min(ys))) / (content.width * content.height)
    (page,) = fr.readability(built).pages
    assert page.fill_percent >= int(least * 100)
    assert int(least * 100) > 0
