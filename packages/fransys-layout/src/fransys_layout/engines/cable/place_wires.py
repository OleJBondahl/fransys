"""Single wires in the cable placer (HA-H1 A1): no cable box, the key text beside the line.

A wire crosses between the rows as a core does, but its line runs straight through the box band
and its text stands one pad beside the line. The harness frame also encloses the wires' columns.
"""

lazy from collections.abc import Sequence

from fransys_layout.engines.cable.place_frame import box_room
from fransys_layout.geometry import WIRING_GRID, Box
lazy from fransys_layout.engines.cable.values import BlockFacts, CoreFacts, PlacedWire

G = WIRING_GRID


def is_wire(facts: BlockFacts, core: CoreFacts) -> bool:
    return core in facts.wires


def upper_stop(facts: BlockFacts, core: CoreFacts, box_y: int) -> int:
    """Where a core's upper run ends: the cable box's top, or for a wire the box band's bottom."""
    return box_y + (box_room(facts)[0] if is_wire(facts, core) else 0)


def text_x(facts: BlockFacts, core: CoreFacts, x: int) -> int:
    """A core's text stands on its axis `x`; a wire's beside the line, clear of it."""
    return x + (facts.text_height + 1) // 2 + facts.pad if is_wire(facts, core) else x


def wire_tops(facts: BlockFacts, tops: Sequence[int]) -> tuple[int, ...]:
    """The top columns of the crossing wires: the last of the crossing cores' columns."""
    count = sum(1 for core in facts.wires if not core.link)
    return tuple(tops[len(tops) - count :])


def envelope(facts: BlockFacts, xs: Sequence[int], pitch: int, box_y: int) -> Box:
    """The box band over the wires' columns `xs` and their keys, for the dashed box only."""
    low, high = min(xs), max(xs)
    key = 2 * ((facts.text_height + 1) // 2) + facts.pad
    left, right = low - pitch // 2 + G, high + max(pitch // 2 - G, key)
    return Box(
        x=left,
        y=box_y,
        width=right - left,
        height=box_room(facts)[0],
    )


def crosses(boxes: Sequence[Box], xs: Sequence[int]) -> bool:
    """Whether a wire's column stands inside a cable box (the block cannot be drawn)."""
    return any(box.x <= x <= box.x + box.width for box in boxes for x in xs)


def text_edges(facts: BlockFacts, wires: Sequence[PlacedWire]) -> list[int]:
    """The right edge of every crossing wire's turned text."""
    flat = {core.conductor for core in facts.wires if not core.link}
    return [w.text_x + (facts.text_height + 1) // 2 for w in wires if w.conductor in flat]
