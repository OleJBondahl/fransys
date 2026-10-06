"""layout-0125: a keep-out cut to the ink drawn."""

from dataclasses import replace

from samples import drawn, placed

from fransys_layout.geometry import Box, Orientation, symbol_geometry
from fransys_layout.stages.finish import ink_keepouts
from fransys_layout.stages.types import LabelKind, PlacedLabel


def _contact():
    geometry = symbol_geometry("make-contact", orientation=Orientation.R180)
    return replace(placed(1, x=96, y=48), geometry=geometry), drawn(1)


def _label(subject, box, *, slot="tag", unplaced=False):
    return PlacedLabel(
        kind=LabelKind.TAG, subject=subject, slot=slot, drawing_set=1, page=1, box=box,
        unplaced=unplaced,
    )  # fmt: skip


def test_the_keepout_shrinks_to_the_body_and_the_labels_taken():
    one, spec = _contact()
    tag = _label(spec.function, Box(x=108, y=48, width=21, height=8))
    marking = _label(spec.ports[0].port, Box(x=98, y=32, width=8, height=8), slot="marking.in")
    (cut,) = ink_keepouts([one], [tag, marking], [spec])
    box = cut.geometry.keepout
    assert box == Box(x=0, y=-16, width=33, height=32)


def test_a_label_not_placed_or_on_another_function_holds_no_room():
    one, spec = _contact()
    far = _label(spec.function, Box(x=108, y=48, width=21, height=8), unplaced=True)
    (cut,) = ink_keepouts([one], [far], [spec])
    assert cut.geometry.keepout == one.geometry.body


def test_a_keepout_grown_beyond_its_slots_is_left_alone():
    one, spec = _contact()
    grown = replace(one.geometry, keepout=Box(x=-14, y=-16, width=200, height=40))
    grown_one = replace(one, geometry=grown)
    assert ink_keepouts([grown_one], [], [spec]) == (grown_one,)
