"""Field case: a cluster of stubs in a page's first row needed more room above than the page kept.
The bug: the staircase of stubs did not fit under the page edge, so it was dropped and the stubs printed over each other.
Fixed by layout-0257: the room above the first row and below the last grows one tier per further cell, up to two."""

from typing import Any

import fransys as fr
import pytest
from _cabinet_design import cabinet_design
from _model_build_cover import cabinet_document

from electrical_symbols import G_PER_MODULE
from fransys_layout.geometry import Box, overlaps
from fransys_model.layout import LinkMarker, Side, layout_of

_CABLES = 4
_CONTENT = Box(x=16, y=16, width=1280, height=822)


@pytest.fixture(scope="module")
def stubs() -> list[tuple[Any, Box]]:
    """Each leaving-line stub as `(page, box)`, the box as drawn."""
    built = fr.build(cabinet_design(_CABLES), cabinet_document("demo-outer"))
    found = []
    for m in layout_of(built.model, LinkMarker).values():
        if m.pairs[0].carrier is None:
            continue
        y = m.y - G_PER_MODULE - m.height if m.facing is Side.N else m.y + G_PER_MODULE
        found.append((m.page, Box(x=m.x - m.width // 2, y=y, width=m.width, height=m.height)))
    return found


def test_a_page_has_three_or_more_stubs_in_a_cluster(stubs: list[tuple[Any, Box]]) -> None:
    per_page = [sum(1 for p, _ in stubs if p == page) for page in {p for p, _ in stubs}]
    assert max(per_page) >= 3


def test_no_two_stub_boxes_of_a_page_meet(stubs: list[tuple[Any, Box]]) -> None:
    meeting = [(a, b) for n, (page, a) in enumerate(stubs) for other, b in stubs[n + 1 :] if page == other and overlaps(a, b)]
    assert meeting == []


def test_every_stub_box_stands_in_the_content_box(stubs: list[tuple[Any, Box]]) -> None:
    out = [
        box
        for _, box in stubs
        if not (
            _CONTENT.x <= box.x
            and _CONTENT.y <= box.y
            and box.x + box.width <= _CONTENT.x + _CONTENT.width
            and box.y + box.height <= _CONTENT.y + _CONTENT.height
        )
    ]
    assert out == []
