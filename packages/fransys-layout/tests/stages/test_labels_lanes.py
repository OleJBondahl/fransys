"""`place_slot_labels` and D2's closed cover of a lane (layout-0083).

Function 2 sits at (104, 96) with the sample symbol: its keep-out box is x 96..152, y 80..112 and
its `in` port (104, 80) faces N, so its lane is x = 104, y 72..80 (one step past the keep-out top).
Function 1 sits at (64, 64) with a tag slot whose anchor and box are hand-made, so a label lands
at any unit: at the slot's home, x = 64 + `at`, y = 64 + `top`, 8 high. A label with an edge ON
the lane covers it; its twin one unit off does not.
"""

import dataclasses
from typing import TYPE_CHECKING

from samples import PROFILE, drawn, hid, placed

from fransys_layout.geometry import Box, Facing, Point, SlotGeometry
from fransys_layout.stages import LabelKind, LabelRequest, place_slot_labels
from fransys_layout.stages.labels import SlotFrame
from fransys_layout.stages.space import Run, covers

if TYPE_CHECKING:
    from fransys_layout.stages import PlacedLabel

_LANE = Run(x=104, y=72, to_x=104, to_y=80)


def _tag_slot(at: int, top: int, side: Facing = Facing.E) -> SlotGeometry:
    """A tag slot anchored at `at`, its box `top` from the symbol's origin (height 8)."""
    return SlotGeometry(
        slot="tag", at=Point(x=at, y=top), side=side, box=Box(x=at, y=top, width=32, height=8)
    )


def _label(at: int, top: int, text: str = "-K1") -> PlacedLabel:
    """Function 1's tag label, its slot anchored at `at` and `top`, beside function 2."""
    one = placed(1, x=64, y=64)
    one = dataclasses.replace(
        one, geometry=dataclasses.replace(one.geometry, slots=(_tag_slot(at, top),))
    )
    request = LabelRequest(kind=LabelKind.TAG, subject=hid("function", 1), slot="tag", text=text)
    labels, findings = place_slot_labels(
        (request,),
        (one, placed(2, x=104, y=96, name="b")),
        (drawn(1), drawn(2)),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    assert findings == ()
    return labels[0]


def test_a_label_with_no_width_covers_no_lane() -> None:
    """Empty text is 0 wide: it overlapped no lane before D2's cover, and blocks nothing still."""
    # UNDO: stages/texts/place_texts.py, `_free`: drop `box.width > 0 and box.height > 0 and`
    label = _label(40, 8, text="")
    assert label.box == Box(x=104, y=72, width=0, height=8)
    assert covers(label.box, _LANE)
