"""The default designation corner is top left, a gap from the wire, inside the content box.

Owner 2026-10-18: "stanard position is top left corner, above the box, some distance from the
wire", for all symbols. The other three corners are fallbacks in the order BL, TR, BR.
"""

from __future__ import annotations

import pytest

from fransys_layout.core import Box
from fransys_layout.core.outputs import Wire

from .label_fixtures import dense, house_options, on_page


def _corner(case, **fields):
    labels, findings = case.run(house_options(**fields))
    return labels[0], findings


def test_the_default_corner_is_top_left_above_the_body() -> None:
    label, findings = _corner(on_page((("S1", 88, 96),)))
    assert label.spot == "TL"
    assert label.box == Box(80, 72, 16, 8)
    assert findings == ()


@pytest.mark.parametrize(("fields", "spot"), [({}, "BL"), ({"label_gap": 0}, "TL")], ids=["within-the-gap-moves-it", "without-a-gap-leaves-top-left"])
def test_a_wire_beside_the_top_left_box_moves_the_label_only_within_the_gap(fields, spot) -> None:
    wire = Wire("n1", 1, ((96, 64), (96, 80)), "straight")  # beside the TL box, 0 apart
    label, _ = _corner(on_page((("S1", 88, 96),), wires=(wire,)), **fields)
    assert label.spot == spot


def test_a_corner_past_the_content_box_is_not_taken() -> None:
    label, findings = _corner(on_page((("S1", 88, 16),)))  # body top at y 0: TL would stand at -8
    assert label.spot == "BL"
    assert label.box.y >= 0
    assert findings == ()


def test_with_no_free_corner_a_finding_names_the_symbol_and_the_label_stays_in_a_corner() -> None:
    labels, findings = dense().run(house_options())
    assert {f.code for f in findings} == {"LABEL_NO_ROOM"}
    assert {f.subject for f in findings} == {"S1", "S2", "S3"}
    assert {x.spot for x in labels} <= {"TL", "BL", "BR", "TR"}


def test_a_spot_with_only_a_near_wire_places_the_label_and_one_under_a_wire_refuses() -> None:
    """R1118: a wire inside label_gap that does not touch is soft, so the only spot places; a wire through it is hard."""
    near = Wire("n1", 1, ((100, 64), (100, 80)), "straight")  # 4 from the TL box, inside the gap of 8
    through = Wire("n1", 1, ((90, 64), (90, 80)), "straight")
    side = Wire("n2", 1, ((76, 72), (76, 112)), "straight")  # walls the turned rungs left of the body (R1849), so only the upright spot is left
    right = Wire("n3", 1, ((108, 64), (108, 176)), "straight")  # walls the upright spot beside the body (R2665), so only TL is left
    soft, found = _corner(on_page((("S1", 88, 96),), wires=(near, side, right)), corner_order=("TL",))
    assert (soft.spot, soft.box, found) == ("TL", Box(80, 72, 16, 8), ())
    _, found = _corner(on_page((("S1", 88, 96),), wires=(through, side, right)), corner_order=("TL",))
    assert {f.code for f in found} == {"LABEL_NO_ROOM"}
