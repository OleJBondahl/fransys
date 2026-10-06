"""layout-0104: the frame gap moves a page right only; every page stays inside on all four sides.

Every keep-out box, label, marker box, outline and route vertex of every page of the cabinet
fixtures lies inside the content box: not above its top (0), not right of its width, not below
its height, and not nearer than the house text gap (8 G, written out) to the left edge for a text.
"""

from collections import defaultdict

import pytest
from layout_cabinet import build_cabinet

from fransys_layout.engines.schematic import run_stages
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.geometry import Box
from fransys_model.kernel import freeze

LEFT_TEXT_GAP = 8


def _boxes(layout) -> dict[tuple[int, int], list[Box]]:
    """Each page's boxes: keep-outs, labels, markers, outlines, and a route vertex as a point."""
    found: dict[tuple[int, int], list[Box]] = defaultdict(list)
    for one in layout.placed:
        k = one.geometry.keepout
        found[one.drawing_set, one.page].append(
            Box(x=one.at.x + k.x, y=one.at.y + k.y, width=k.width, height=k.height)
        )
    for label in layout.labels:
        found[label.drawing_set, label.page].append(label.box)
    for marker in layout.markers:
        found[marker.drawing_set, marker.page].append(marker.box)
    for outline in layout.outlines:
        found[outline.drawing_set, outline.page].append(outline.box)
    for route in layout.routes:
        found[route.drawing_set, route.page].extend(
            Box(x=p.at.x, y=p.at.y, width=0, height=0) for p in route.points
        )
    return found


@pytest.mark.parametrize(
    "kwargs", [{}, {"reverse": True}, {"second_location": True}, {"extra_relay": True}]
)
def test_every_page_stays_inside_the_content_box_on_all_four_sides(kwargs) -> None:
    model = freeze(build_cabinet(**kwargs))
    inputs = read_inputs(model)
    layout, _, _ = run_stages(model, inputs)
    width, height = inputs.sheet.content_width, inputs.sheet.content_height
    pages = _boxes(layout)
    assert len(pages) >= 1
    for page, boxes in pages.items():
        assert min(b.y for b in boxes) >= 0, ("top", page)
        assert max(b.x + b.width for b in boxes) <= width, ("right", page)
        assert max(b.y + b.height for b in boxes) <= height, ("bottom", page)
        assert min(b.x for b in boxes) >= 0, ("left", page)
    texts = [label.box.x for label in layout.labels]
    assert min(texts) >= LEFT_TEXT_GAP, "a text stands a gap from the left edge"
