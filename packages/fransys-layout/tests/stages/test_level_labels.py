"""F2 (layout deep dive, designer's ruling): a device terminal's tag stands on the W of its
circle and its marking on the E, both level with the circle's centre.

Can-fail, checked by hand: without the `level` branch in `_labelling.home` both boxes stay at
the tag slot above the circle and the first assertion fails.
"""

import dataclasses

from samples import PROFILE, hid, placed, through_geometry

from fransys_layout.geometry import Box, Facing, Point, SlotGeometry
from fransys_layout.stages import LabelKind, LabelRequest
from fransys_layout.stages._labelling import home


def _terminal():
    """A circle 16 wide on its wire, its tag slot above it on the E, as a terminal's."""
    geometry = dataclasses.replace(
        through_geometry(half_height=8),
        slots=(
            SlotGeometry(
                slot="tag",
                at=Point(x=4, y=-26),
                side=Facing.E,
                box=Box(x=4, y=-30, width=48, height=8),
            ),
        ),
    )
    return dataclasses.replace(placed(1, x=96, y=200), geometry=geometry)


def _box(slot: str) -> Box:
    request = LabelRequest(
        kind=LabelKind.TAG, subject=hid("function", 1), slot=slot, text="A2", level=True
    )
    return home(request, _terminal(), PROFILE).box


def test_a_device_terminals_tag_and_marking_stand_level_with_its_circle() -> None:
    strip, point = _box("tag.strip"), _box("tag.point")
    centre = 200  # the circle's centre, on the page
    assert strip.y + strip.height // 2 == centre == point.y + point.height // 2
    assert strip.x + strip.width <= 96 - 8  # W of the circle
    assert point.x >= 96 + 8  # E of the circle
