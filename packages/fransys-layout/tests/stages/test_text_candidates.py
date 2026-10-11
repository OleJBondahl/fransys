"""`stages.texts.candidates`: the table, its one ranking and the owner-relative box.

Hand-built values only, no pipeline. The expected boxes are hard-coded numbers: the link
marker's anchoring (one wiring-grid step out, centred on the port, which
`references.marker_boxes` stands its boxes through) and
a wire label's (flush above or right of its segment, centred, as `place_wire_labels` put it
before it placed through `place_texts`), with odd sizes so their floor divisions are pinned.
"""

import pytest

from fransys_layout.geometry import Box, Facing, LayoutError, Point
from fransys_layout.stages.texts.candidates import (
    DEFAULT_TABLE,
    Candidate,
    CandidateTable,
    Side,
    TextKind,
    box_of,
    ranked_candidates,
    stub_anchor,
)

_TEXT = (30, 7)  # an invented text: 30 wide, 7 high


def test_a_tag_ranks_its_own_sides_steps_nearest_first_then_its_mirrors() -> None:
    """A tag stands at its own side first, the nearest step first, down before up,
    then its mirror across the body, same order: with Facing.W it is W then E, with Facing.E
    it is E then W. Last come the steps past a vertical marker box beside the port,
    again its own side first and then the mirror, so a text with a near place never moves."""
    near, past = (0, 7, -7, 14, -14), (21, -21, 28, -28)
    for own, mirror in ((Facing.W, Facing.E), (Facing.E, Facing.W)):
        found = ranked_candidates(TextKind.TAG, own, _TEXT, DEFAULT_TABLE)
        assert found == tuple(
            Candidate(side=side, offset=offset, row=False)
            for offsets in (near, past)
            for side in (own, mirror)
            for offset in offsets
        )


def test_a_text_at_its_owners_facing_with_an_owner_of_no_facing_raises() -> None:
    """A reference's row stands at its port's facing; with no facing there is no candidate."""
    with pytest.raises(LayoutError, match="its owner has none"):
        ranked_candidates(TextKind.REFERENCE, None, _TEXT, DEFAULT_TABLE)


def test_the_steps_are_the_texts_own_height() -> None:
    """A step is one height of the text itself, so a taller text steps further."""
    table: CandidateTable = frozendict({TextKind.TAG: (Side(facing=Facing.S, steps=(0, 1, -2)),)})
    assert ranked_candidates(TextKind.TAG, None, (10, 13), table) == (
        Candidate(side=Facing.S, offset=0, row=True),
        Candidate(side=Facing.S, offset=13, row=True),
        Candidate(side=Facing.S, offset=-26, row=True),
    )


@pytest.mark.parametrize(
    ("facing", "expected"),
    [
        (Facing.E, Box(x=88, y=49, width=43, height=15)),
        (Facing.W, Box(x=29, y=49, width=43, height=15)),
        (Facing.N, Box(x=59, y=33, width=43, height=15)),
        (Facing.S, Box(x=59, y=64, width=43, height=15)),
    ],
)
def test_a_port_text_stands_one_stub_step_out_centred_on_the_port(
    facing: Facing, expected: Box
) -> None:
    """At port (80, 56): E x = 80 + 8, W x = 80 - 8 - 43, N/S x = 80 - 43 // 2; y likewise."""
    candidate = ranked_candidates(TextKind.REFERENCE, facing, (43, 15), DEFAULT_TABLE)[0]
    assert box_of(candidate, stub_anchor(Point(x=80, y=56)), (43, 15)) == expected


def test_an_offset_moves_the_box_along_its_side() -> None:
    """An E or W offset moves y; an N or S offset moves x."""
    anchor = Box(x=0, y=0, width=20, height=10)
    assert box_of(Candidate(side=Facing.W, offset=7), anchor, (6, 4)) == Box(
        x=-6, y=10, width=6, height=4
    )
    assert box_of(Candidate(side=Facing.S, offset=-5, row=True), anchor, (6, 4)) == Box(
        x=2, y=10, width=6, height=4
    )
