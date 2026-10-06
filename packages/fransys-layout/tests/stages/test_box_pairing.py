"""layout-0107: a box stands over the pin group it feeds, pin under pin (hand-made values, D8).

Box 1 is the fed one: top pins `a1 a2` (fed by box 2) and `b1 b2` (fed by box 3), a bottom pin
`z`. Boxes 2 and 3 are the feeders: bottom pins named for the group they feed, in any order.
"""

from pairing_fixture import PROFILE, box, feed, pair
from samples import placed

from fransys_layout.stages.boxes import box_sides, paired_boxes
lazy from fransys_layout.stages import DrawnFunction


def _x(box: DrawnFunction, name: str) -> int:
    return next(g.at.x for g in box.geometry.ports if g.name == name)


def test_the_fed_pins_take_the_feeders_pin_offsets_in_a_slot_each() -> None:
    """Group a's pins stand a feeder-2 pin pitch apart; group b starts a slot on."""
    # UNDO: stages/box_pairing.py:_fed_over, `at[name] = start[...] + pin - body.x` -> `... = 0`
    fed, two, _three = pair()
    assert _x(fed, "a2") - _x(fed, "a1") == _x(two, "q2") - _x(two, "q1")
    slot = two.geometry.keepout.width + PROFILE.column_gap
    assert _x(fed, "b1") - _x(fed, "a1") >= slot


def test_the_feeders_paired_pins_follow_the_fed_order() -> None:
    """Box 2 was drawn `q2 q1`, wired `a2`-`q2` first; the fed group is `a1 a2`: `q1` is left."""
    # UNDO: stages/box_pairing.py:_feeder_order, `block = [b for a in order ...]` ->
    #     `block = [g.name for g in feeder.geometry.ports]` (the feeder keeps its order)
    _, two, _ = pair()
    assert _x(two, "q1") < _x(two, "q2")


def test_a_feeder_and_its_fed_box_are_marked_and_the_feeders_axis_is_a_paired_pin() -> None:
    """The feeder's column axis is its first paired pin, so attaching it aligns the group."""
    fed, two, _ = pair()
    assert fed.fed_by != ()
    assert two.feeds == fed.function
    assert (two.primary_in, two.primary_out) == (None, "q1")


def test_a_pin_on_the_wrong_side_leaves_the_boxes_as_they_were() -> None:
    """A fed pin that is not on top is no pairing: the boxes draw as today."""
    boxes = (box(1, ("a1",), ("a2", "z")), box(2, (), ("q1", "q2")))
    result = paired_boxes(boxes, (feed(2, (("a1", "q1"), ("a2", "q2"))),), PROFILE)
    assert result == boxes


def test_box_sides_leaves_a_paired_box_alone() -> None:
    """`_turned_box` would redraw the pins at the default pitch; a paired box keeps its x."""
    # UNDO: stages/boxes.py:_paired, `return bool(one.fed_by) or one.feeds is not None` ->
    #     `return False` (box_sides re-sorts the paired pins)
    boxes = pair()
    spots = tuple(placed(n, x=0, y=0) for n in (1, 2, 3))
    after = box_sides(spots, boxes, (), ({}, {}, {}))
    assert after == boxes
