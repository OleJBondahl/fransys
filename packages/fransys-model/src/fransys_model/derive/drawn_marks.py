"""The cable drawing's pair bracket values: what a bracket joins and where its zone stands (CC10).

Read through `cable_drawing`, never directly: layout places the bracket and render prints it.
"""

from typing import Any

from fransys_model.kernel import value
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab import Item


@value
class DrawnBracket:
    """A bracket joining the rows of one pair's two neighbouring cores, with its label."""

    cable: Id[Item]
    label: str
    core_a: Id[Any]
    core_b: Id[Any]


@value
class PairRoom:
    """Where a block's pair brackets stand, in grid units below a cable box's top.

    The label's top, the bracket's line, the ends of its ticks, and the room the zone adds
    below the heading, which the core texts start under.
    """

    head: int
    label: int
    line: int
    tick: int
    room: int


def pair_room(text_height: int, pad: int, grid: int) -> PairRoom:
    """The bracket zone under a cable box's heading, whole grid units (CC10)."""
    head = -(-(2 * pad + text_height) // grid) * grid
    line = head + text_height + pad
    return PairRoom(
        head=head,
        label=head,
        line=line,
        tick=line + pad,
        room=-(-(text_height + 3 * pad) // grid) * grid,
    )
