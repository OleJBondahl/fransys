"""Field case: the two-pin headers a fan-out harness ends on are drawn overlapping.

The engineering shape: a board offers a ten-pin header. One loom's plug mates it and the loom
runs to three two-pin headers, two wires to each.

The bug: the three header boxes are placed one box-width apart or less, so they stand
over each other on the page, their texts overprint and the fan-out's branch labels sit on one
another. TEXT_OVERLAP reports two of the pairs; the boxes themselves are never compared.
CLEANUP-ROUND-2 CL8 held the row (the round 1 rows 4 and 6 and the fan-out of the tall
page). Fixed by layout-0233: a boxed pin view holds its box's width in its column, flipped or not.
"""

import sys
import tempfile
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import fransys as fr
import fransys_parts
from _drawn_pages import drawn_pages

sys.path.insert(
    0, str(Path(__file__).parent)
)  # the sibling case whose board and library this reuses
from test_a_harness_line_on_an_overfull_page_still_routes import (
    WIRE,
    _board,
    _library,
    _Top,
)

from fransys_model.kernel import merge


@cache
def _built() -> fr.BuildResult:
    @fr.unit("fld-top", revision=1, interface_version=1, date="2026-10-14", text="t", by="X")
    def top(u: Any) -> _Top:
        board = u.add(_board, "A1", unused=("j1", "j2", "j3", "j4", "j5"))
        plug = u.device("J1", "FLD-PLG-10", parent=u.harness("T1"), name="tp")
        u.mate(plug, board.j6)
        for k, name in enumerate("ABC"):
            far = u.device(f"X{name}", "FLD-HDR-2")
            u.detail.wire(plug[str(2 * k + 1)], far["1"], wire=WIRE)
            u.detail.wire(plug[str(2 * k + 2)], far["2"], wire=WIRE)
        return _Top()

    root = Path(tempfile.mkdtemp())
    draft = merge(fransys_parts.load("demo_parts"), fransys_parts.load_path(_library(root / "lib")))
    d = fr.Design(draft)
    d.add(top, "U1")
    (root / "cover.md").write_text("# Top\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset("cabinet_schematic"), "fld-top", cover=root / "cover.md")
    return fr.build(d, doc)


def _far_boxes() -> dict[str, list[tuple[Any, Box]]]:
    """Each far header's (page, box) pairs: the tag texts the core path prints for it."""
    found: dict[str, list[tuple[Any, Box]]] = {}
    for page, drawing in drawn_pages(_built().model).items():
        for text in drawing.texts:
            name = text.text.split(":")[0].removeprefix("-U1-").removeprefix("-")
            if name in {"XA", "XB", "XC"}:
                found.setdefault(name, []).append((page, text.box))
    return found


def test_the_three_far_headers_are_drawn_on_one_page() -> None:
    boxes = _far_boxes()
    assert len(boxes) == 3, boxes
    assert len({page for texts in boxes.values() for page, _ in texts}) == 1


def _overlaps(a: Box, b: Box) -> bool:
    return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h


def test_no_two_far_header_boxes_overlap() -> None:
    boxes = _far_boxes()
    assert len(boxes) == 3
    heads = list(boxes.values())
    assert not [
        (a, b)
        for i, one in enumerate(heads)
        for other in heads[i + 1 :]
        for pa, a in one
        for pb, b in other
        if pa == pb and _overlaps(a, b)
    ]


def test_the_page_reports_no_text_overlap() -> None:
    assert len(_far_boxes()) == 3
    assert "TEXT_OVERLAP" not in {f.code for f in _built().findings}


if TYPE_CHECKING:
    from fransys_layout.core import Box
