"""The default designation corner is top left, a gap from the wire, inside the content box.

Owner 2026-10-18: "stanard position is top left corner, above the box, some distance from the
wire", for all symbols. The other three corners are fallbacks in the order BL, BR, TR.
"""

from __future__ import annotations

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


def test_a_wire_within_the_gap_moves_the_label_to_a_fallback_corner() -> None:
    wire = Wire("n1", 1, ((96, 64), (96, 80)), "straight")  # beside the TL box, 0 apart
    label, _ = _corner(on_page((("S1", 88, 96),), wires=(wire,)))
    assert label.spot == "BL"


def test_without_a_gap_the_same_wire_leaves_top_left_free() -> None:
    wire = Wire("n1", 1, ((96, 64), (96, 80)), "straight")
    label, _ = _corner(on_page((("S1", 88, 96),), wires=(wire,)), label_gap=0)
    assert label.spot == "TL"


def test_a_corner_past_the_content_box_is_not_taken() -> None:
    label, findings = _corner(on_page((("S1", 88, 16),)))  # body top at y 0: TL would stand at -8
    assert label.spot == "BL"
    assert label.box.y >= 0
    assert findings == ()


def test_with_no_free_corner_a_finding_names_the_symbol_and_the_label_stays_in_a_corner() -> None:
    labels, findings = dense().run(house_options())
    assert {f.code for f in findings} == {"ANNEX_UNPLACED"}
    assert {f.subject for f in findings} == {"S1", "S2", "S3"}
    assert {x.spot for x in labels} <= {"TL", "BL", "BR", "TR"}
