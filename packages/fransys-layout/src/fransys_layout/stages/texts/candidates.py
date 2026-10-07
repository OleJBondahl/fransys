"""D3's candidate table and its one ranking (layout-0090 S2): where a text may stand, best first.

A text stands beside its owner: a port's stub, a function's slot, a route's segment. Its
candidates are owner-relative (`Candidate`): a side of the owner, an offset along that side,
and whether it stands in a row above or below. Nothing is absolute until `box_of` puts one
candidate beside the owner's placed anchor, so `place` can rank before any position exists.

`ranked_candidates` is the one ranking. `place` reserves its first candidate (Room, S11) and
`texts` walks the whole list (D3); neither ranks on its own (S2).

The table is data in `conventions/texts.py`, one row per kind: the sides in
try-order, and along each side its steps in try-order. Its defaults are the designer's and
follow today's anchoring (D13, D14): a tag, a
marking and a cross-reference on their slot's own side first, then its mirror across the body
(S18, owner-relative), a reference or a stub at its stub. Along a side the nearest step comes
first, down (or right) before up (or left). A row's steps are the whole bound of its moves:
the placer adds only the content box, never the owner's keep-out (S18, amended after 2b-6). No
kind stands above or below its function by default, since no slot label does today; a row is
a data change there.
The owner judges the defaults after order step 7 (D3), and every change is a change to that
file. `PRIORITY` is the kind's part of the placer's key (S15).
"""

from enum import Enum
from typing import Any

from fransys_layout.conventions import FACTS, fact, keyed, validate
from fransys_layout.conventions.texts import TABLE
from fransys_layout.geometry import OPPOSITE, WIRING_GRID, Box, Facing, LayoutError, Point
from fransys_model.kernel import register_enum, value


@register_enum
class TextKind(Enum):
    """What a text is, for D3's table and key order (not `LabelKind`, which `write` maps)."""

    REFERENCE = "reference"
    STUB = "stub"
    TAG = "tag"
    MARKING = "marking"
    CONTACT_IMAGE = "contact_image"
    CROSS_REFERENCE = "cross_reference"
    POWER = "power"
    HARNESS_LINE = "harness_line"


@value
class Candidate:
    """One owner-relative place a text may stand (S2), made absolute only by `box_of`."""

    side: Facing
    offset: int
    row: bool = False
    out: int = 0


@value
class Side:
    """One side of a table row: where the text stands, and its steps along it (D14)."""

    facing: Facing | None
    steps: tuple[int, ...]
    mirror: bool = False


# One row per kind: its sides in try-order.
type CandidateTable = frozendict[TextKind, tuple[Side, ...]]


@fact("text_kind", kind="drawing", values=tuple(k.value for k in TextKind))
def _text_kind(text: TextKind) -> str:
    """The kind of a text, for D3's table."""
    return text.value


validate(TABLE, FACTS)
_ROWS: dict[str, Any] = keyed(TABLE, "text_kind")  # row: (priority, ((facing, steps, mirror), ...))


def _side(one: tuple[str | None, tuple[int, ...], bool]) -> Side:
    facing, steps, mirror = one
    return Side(facing=None if facing is None else Facing(facing), steps=steps, mirror=mirror)


DEFAULT_TABLE: CandidateTable = frozendict(
    {kind: tuple(_side(one) for one in _ROWS[kind.value][1]) for kind in TextKind}
)

# S15: a reference and a stub first, a tag and a marking next, then a contact image. A lower
# number is placed first.
PRIORITY: frozendict[TextKind, int] = frozendict({kind: _ROWS[kind.value][0] for kind in TextKind})


def ranked_candidates(
    kind: TextKind, owner_facing: Facing | None, size: tuple[int, int], table: CandidateTable
) -> tuple[Candidate, ...]:
    """The text's candidates, best first, from `table`'s row for `kind` (D3's key order)."""
    found = []
    for side in table[kind]:
        facing = owner_facing if side.facing is None else side.facing
        if facing is None:
            msg = f"a {kind.value} text stands at its owner's facing, and its owner has none"
            raise LayoutError(msg)
        if side.mirror:
            facing = OPPOSITE[facing]
        row = facing in (Facing.N, Facing.S)
        found.extend(Candidate(side=facing, offset=step * size[1], row=row) for step in side.steps)
    return tuple(found)


def box_of(candidate: Candidate, anchor: Box, size: tuple[int, int]) -> Box:
    """The page box of `candidate` for a text of `size` beside `anchor` (layout-0038, 6.7)."""
    width, height = size
    across_x = anchor.x + anchor.width // 2 - width // 2 + candidate.offset
    across_y = anchor.y + anchor.height // 2 - height // 2 + candidate.offset
    out = candidate.out
    match candidate.side:
        case Facing.E:
            return Box(x=anchor.x + anchor.width + out, y=across_y, width=width, height=height)
        case Facing.W:
            return Box(x=anchor.x - width - out, y=across_y, width=width, height=height)
        case Facing.N:
            return Box(x=across_x, y=anchor.y - height - out, width=width, height=height)
        case Facing.S:
            return Box(x=across_x, y=anchor.y + anchor.height + out, width=width, height=height)


def stub_anchor(at: Point) -> Box:
    """A port's anchor: its point grown one stub step on every side (layout-0038's stub)."""
    return Box(
        x=at.x - WIRING_GRID, y=at.y - WIRING_GRID, width=2 * WIRING_GRID, height=2 * WIRING_GRID
    )
