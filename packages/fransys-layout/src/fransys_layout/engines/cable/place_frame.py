"""The cable placer's harness frame: cable boxes side by side and the dashed box (CT5-4, CD9).

A cable box spans its cores' top columns, inset one grid unit each side so two never share an
edge; a cable with no cores has a heading-wide box after the others. The dashed box clears them
by one grid unit and reaches left until its label ends one pad before the first wire.
"""

from itertools import pairwise
lazy from collections.abc import Sequence

from fransys_layout.engines.cable.values import BlockFacts, PlacedCable
from fransys_layout.geometry import WIRING_GRID, Box, snap_up

G = WIRING_GRID
BOX = 4 * G  # the cable box's least height

type Spans = tuple[tuple[int, int] | None, ...]


def box_room(facts: BlockFacts) -> tuple[int, int]:
    """The cable boxes' height and their core texts' centre below a box's top (CD8, N1).

    The box holds the heading and the longest crossing core's text, upright on its axis (a link's
    stands at its row); every box shares the height.
    """
    head = snap_up(2 * facts.pad + facts.text_height)
    texts = (core.text_width for core in facts.cores if not core.link)
    longest = max(texts, default=0)
    height = max(BOX, head + snap_up(longest + 2 * facts.pad, grid=2 * G))
    return height, head + (height - head) // (2 * G) * G


def dash_top(lone_box_y: int) -> int:
    """The dashed box's top: one grid unit above where a lone cable's box would stand."""
    return max(0, lone_box_y - G)


def box_top(facts: BlockFacts, lone_box_y: int) -> int:
    """The cable boxes' top: the label row, then one grid unit of clearance."""
    return snap_up(dash_top(lone_box_y) + facts.pad + facts.text_height) + G


def spans(owners: tuple[int, ...], tops: tuple[int, ...], count: int) -> Spans:
    """Each cable's first and last top column x, or None for a cable with no cores."""
    found: list[tuple[int, int] | None] = [None] * count
    for owner, x in zip(owners, tops, strict=True):
        low, high = found[owner] or (x, x)
        found[owner] = (min(low, x), max(high, x))
    return tuple(found)


def _wide(facts: BlockFacts, cable: int) -> int:
    return snap_up(facts.cables[cable].heading_width + 2 * facts.pad)


def boxes_fit(facts: BlockFacts, found: Spans, pitch: int) -> bool:
    """Whether every cored cable's box is wide enough for its heading (Q2)."""
    return all(
        span is None or span[1] - span[0] + pitch - 2 * G >= _wide(facts, n)
        for n, span in enumerate(found)
    )


def cable_boxes(
    facts: BlockFacts, found: Spans, pitch: int, box_y: int, x0: int
) -> tuple[PlacedCable, ...] | None:
    """The cable boxes by designation, or None when two cored boxes would overlap (CD-H6)."""
    height = box_room(facts)[0]
    placed: dict[int, Box] = {
        n: Box(
            x=span[0] - pitch // 2 + G,
            y=box_y,
            width=span[1] - span[0] + pitch - 2 * G,
            height=height,
        )
        for n, span in enumerate(found)
        if span is not None
    }
    cored = list(placed.values())
    if any(one.x + one.width >= two.x for one, two in pairwise(cored)):
        return None
    right = max((box.x + box.width for box in cored), default=x0 - G)
    for n in range(len(found)):
        if n not in placed:
            width = _wide(facts, n)
            placed[n] = Box(x=right + 2 * G, y=box_y, width=width, height=height)
            right += 2 * G + width
    return tuple(
        PlacedCable(cable=cable.cable, external=cable.external, box=placed[n])
        for n, cable in enumerate(facts.cables)
    )


def dashed_box(label: int, boxes: Sequence[Box], first_x: int | None, y: int) -> Box:
    """The harness box around `boxes`, from `y` to one grid unit below them (Q4)."""
    left = min(box.x for box in boxes) - G
    if first_x is not None:
        left = min(left, first_x - label)
    left -= left % G
    right = snap_up(max(max(box.x + box.width for box in boxes) + G, left + label))
    return Box(x=left, y=y, width=right - left, height=boxes[0].y + boxes[0].height + G - y)
