"""Cable engine, row links: their tracks, runs and text (CT5-LINK, CD5 and CD8 at L1, layout-0148).

A link joins two pins of one row. One run leaves each pin toward the cable box, to a track of the
band beside that row, and a straight run joins the two corners. The record keeps it in the two
runs a core has: `run_a = (pin_a, corner_a, corner_b)`, `run_b = (pin_b, corner_b)`. The text is
horizontal, on the side of the track away from the pins, in a room of a grid unit plus a text
height, at the nearest place clear of every vertical wire.
"""

from dataclasses import dataclass
from itertools import pairwise
lazy from collections.abc import Mapping, Sequence

from fransys_layout.engines.cable.channel import plan_links
from fransys_layout.engines.cable.values import BlockFacts, CoreFacts, PlacedEnd, PlacedWire
from fransys_layout.geometry import WIRING_GRID, Point

G = WIRING_GRID

type Line = tuple[Point, ...]


@dataclass(frozen=True, slots=True)
class Link:
    """One placed link: its core, the x of its two pins (`end_a`'s first), their y and row."""

    core: CoreFacts
    a: int
    b: int
    y: int
    top: bool

    @property
    def pins(self) -> tuple[Point, Point]:
        return Point(x=self.a, y=self.y), Point(x=self.b, y=self.y)


def room(facts: BlockFacts) -> int:
    """The height of a link track's room: a grid unit and the text's height."""
    return G + facts.text_height


def links_of(facts: BlockFacts, ends: tuple[PlacedEnd, ...]) -> tuple[Link, ...]:
    """The block's links in core-key order whose pins stand in `ends`."""
    where = {cell.port: (cell.x, end) for end in ends for cell in end.cells}
    found = []
    for core in (c for cable in facts.cables for c in cable.cores if c.link):
        if core.end_a not in where:
            continue
        (a, end), (b, _) = where[core.end_a], where[core.end_b]
        y = end.y + end.height if end.top else end.y
        found.append(Link(core=core, a=a, b=b, y=y, top=end.top))
    return tuple(found)


def _levels(links: Sequence[Link]) -> tuple[int, ...]:
    """Each top-row link's track in the upper band, from 1, filled by left edge."""
    return plan_links([(link.core.key, link.a, link.b) for link in links if link.top])


def lift(facts: BlockFacts, ends: tuple[PlacedEnd, ...]) -> int:
    """How far the upper band grows for the top row's links (zero when it has none)."""
    return room(facts) * max(_levels(links_of(facts, ends)), default=0)


def lower(links: Sequence[Link]) -> tuple[Link, ...]:
    """The links of the bottom row: nets of the lower band's channel."""
    return tuple(link for link in links if not link.top)


def _line(link: Link, y: int) -> Line:
    a, b = link.pins
    return a, Point(x=link.a, y=y), Point(x=link.b, y=y), b


def upper_lines(facts: BlockFacts, links: Sequence[Link]) -> dict[int, Line]:
    """Each top-row link's polyline, pin to pin, by core key: tracks one room apart (CD8 at L1)."""
    top = [link for link in links if link.top]
    return {
        link.core.key: _line(link, link.y + G + (level - 1) * room(facts))
        for link, level in zip(top, _levels(links), strict=True)
    }


def _blocked(lines: Sequence[Line], low: int, high: int) -> list[tuple[int, int]]:
    """The x of every vertical run that enters the open band `low` to `high`."""
    return [
        (p.x, p.x)
        for line in lines
        for p, q in pairwise(line)
        if p.x == q.x and min(p.y, q.y) < high and max(p.y, q.y) > low
    ]


def _left(width: int, wanted: int, blocked: Sequence[tuple[int, int]], gap: int) -> int:
    """The left edge nearest `wanted` where a text `width` wide meets no blocked x, or `wanted`."""
    for step in range(width + 2 * G + abs(wanted)):
        for left in (wanted - step, wanted + step):
            if left >= 0 and all(
                left + width + gap < low or high + gap < left for low, high in blocked
            ):
                return left
    return wanted


def _wire(facts: BlockFacts, link: Link, line: Line, left: int) -> PlacedWire:
    """The record of one link: its runs, and its text from `left` beside the track."""
    y = line[1].y
    return PlacedWire(
        conductor=link.core.conductor,
        run_a=line[:3],
        run_b=(line[3], line[2]),
        text_x=left + link.core.text_width // 2,
        text_y=y + room(facts) // 2 if link.top else y - room(facts) // 2,
        stub_a=False,
        stub_b=False,
    )


def link_wires(
    facts: BlockFacts, links: Sequence[Link], lines: Mapping[int, Line], others: Sequence[Line]
) -> tuple[PlacedWire, ...]:
    """Every link's `PlacedWire`; `lines` holds each link's polyline, `others` the other wires.

    A text stays clear of every vertical wire in its room and of the texts placed before it.
    """
    everything = [*others, *lines.values()]
    found: list[PlacedWire] = []
    taken: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for link in links:
        line, width = lines[link.core.key], link.core.text_width
        y = line[1].y
        slot = (y, y + room(facts)) if link.top else (y - room(facts), y)
        blocked = taken.setdefault(slot, _blocked(everything, *slot))
        left = _left(width, (link.a + link.b - width) // 2, blocked, facts.pad)
        blocked.append((left, left + width))
        found.append(_wire(facts, link, line, left))
    return tuple(found)
