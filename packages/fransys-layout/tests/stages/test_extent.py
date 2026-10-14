"""A column's extent reads every box it draws (layout-0175): hand-made values, no engine."""

from unittest.mock import patch

from fransys_el import OPTIONS
from layout_cabinet import build_cabinet
from samples import PROFILE, drawn, hid, placed

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.geometry import Box, text_width
from fransys_layout.stages import LabelKind, LabelRequest
from fransys_layout.stages.extent import column_extent, drawn_boxes, marker_boxes, room_boxes
from fransys_model.kernel import freeze

FUNCTION = hid("function", 1)


def test_a_long_tag_is_a_box_of_its_function_past_the_keep_out() -> None:
    """The tag slot is E at x 16 from the origin 104; a long text reaches past the keep-out."""
    # UNDO: stages/extent.py:drawn_boxes, `found[...].append(box)` -> `pass` (no label counts)
    text = "a long tag text"
    one = placed(1, x=104, y=0)
    request = LabelRequest(kind=LabelKind.TAG, subject=FUNCTION, slot="tag", text=text)

    found = drawn_boxes([((request,), (one,), (drawn(1),))], PROFILE)

    (box,) = found[1, 1, FUNCTION]
    assert box.x + box.width == 104 + 16 + text_width(text, height=PROFILE.text_height)
    assert box.x + box.width > 104 + 48  # past the keep-out's right edge
    assert column_extent([box, Box(x=96, y=0, width=8, height=8)]).x == 96


def test_a_marker_box_joins_the_boxes_of_the_function_its_decision_names() -> None:
    """The decision names the function; the marker the box; they pair in order."""

    # UNDO: stages/extent.py:marker_boxes, `.append(marker.box)` -> `.append(Box(0, 0, 0, 0))`
    class _Decision:
        drawing_set, page, function = 1, 2, FUNCTION

    class _Marker:
        box = Box(x=300, y=4, width=40, height=8)

    found = marker_boxes([_Decision()], [_Marker()], {})  # ty: ignore[invalid-argument-type] -- test doubles

    assert found == {(1, 2, FUNCTION): [_Marker.box]}


def test_the_engine_packs_every_page_on_the_labels_and_markers_it_draws() -> None:
    """`place_pages` hands `placed_widths` the label and marker boxes of the placed pages."""
    # UNDO: stages/pagerun.py:place_pages, `placed_widths(..., extras)` -> `placed_widths(...)`
    from fransys_layout.stages import pagerun

    seen = []
    real = pagerun.placed_widths

    def spy(widths, placed_all, gap, extras=None):
        seen.append(extras)
        return real(widths, placed_all, gap, extras)

    with patch.object(pagerun, "placed_widths", spy):
        model = freeze(build_cabinet(second_location=True, side_terminals=True))
        stage_results(model, read_inputs(model, options=OPTIONS))

    assert seen
    assert all(extras for extras in seen)


def test_room_boxes_stand_below_and_beside_the_keep_out() -> None:
    """A room of (12, 20) is a box below and one beside the keep-out (96, 32) 56 by 32."""
    # UNDO: stages/extent.py:room_boxes, drop the beside box
    one = placed(1, x=104, y=48)
    key = (one.column, one.function)

    assert room_boxes([one], {key: (12, 20)}) == {
        key: [Box(x=96, y=64, width=56, height=12), Box(x=152, y=32, width=20, height=32)]
    }
    assert room_boxes([one], {key: (0, 20)}) == {key: [Box(x=152, y=32, width=20, height=32)]}
