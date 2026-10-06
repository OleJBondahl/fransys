"""S9, S2, S16: where a reference or stub text stands beside its port, in its symbol's frame.

One home for both readers of a `MarkerDecision`'s place: `texts` builds the marker there on the
placed page (`markers.link_markers`), and `place` reserves room for it before, as the page's
margin above a first row or below a last one (Room's N or S call, `page_texts` and `end_boxes`,
S16). `symbol_port` finds the symbol port a model port is drawn at, `leave_port` says which of
its symbol's ports the text stands at (`Leave`), `candidate_box` gives its box at its
first-ranked candidate beside that port, and `merged` adds a merged stub's line (S5);
`_text_box` is the two together, the whole box the text takes. A C21 run's one box is
`run_box`, which `texts` builds on the placed page as the run's marker box (S17, S20).
"""

import dataclasses
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import (
    WIRING_GRID,
    Box,
    Facing,
    LayoutError,
    text_width,
)
from fransys_layout.stages.markers import stand_against_content_edge
from fransys_layout.stages.references.marker_boxes import reads_along, reference_size
from fransys_layout.stages.references.types import Leave
from fransys_model.derive.drawing_text import off_stub_line

from .candidates import DEFAULT_TABLE, TextKind, box_of, ranked_candidates, stub_anchor

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.geometry import Point, PortGeometry, SymbolGeometry
    from fransys_layout.stages.references.types import MarkerDecision, Page
    from fransys_layout.stages.types import (
        Column,
        Connection,
        DrawnFunction,
        Profile,
        SheetFormat,
        StubText,
    )
    from fransys_model.kernel import Id

    # `(port, drawing set, page)` of every connection end drawn on that page (`page_wiring`)
    type Wired = frozenset[tuple[Id[Any], int, int]]


@dataclass(frozen=True, slots=True)
class PageTexts:
    """S16: one page's reference and stub texts as Room reserves them, by owner, and its wiring."""

    owned: Mapping[Id[Any], tuple[MarkerDecision, ...]]
    wired: frozenset[Id[Any]]
    joined: frozenset[Id[Any]] = frozenset()


def page_texts(
    markers: tuple[MarkerDecision, ...],
    wired: Wired,
    *,
    sheet: SheetFormat,
    profile: Profile,
    joined: frozenset[Id[Any]] = frozenset(),
) -> dict[Page, PageTexts]:
    """Each page's `PageTexts`, by `(drawing set, page)`, from the decisions and wiring (S16)."""
    line = reference_size(sheet, profile, lines=1)[1]
    owned: dict[Page, dict[Id[Any], list[MarkerDecision]]] = {}
    for one in markers:
        page = (one.drawing_set, one.page)
        on_page = owned.setdefault(page, {})
        reserved = dataclasses.replace(one, lines=1, size=(one.size[0], line))
        on_page.setdefault(one.function, []).append(reserved)
    ports = wired_by_page(wired)
    return {
        page: PageTexts(
            owned={function: tuple(texts) for function, texts in by_function.items()},
            wired=ports.get(page, frozenset()),
            joined=joined,
        )
        for page, by_function in owned.items()
    }


def wired_by_page(wired: Wired) -> dict[Page, frozenset[Id[Any]]]:
    """`wired`'s ports by `(drawing set, page)`: the model ports with a wire drawn on each page."""
    found: dict[Page, set[Id[Any]]] = defaultdict(set)
    for port, drawing_set, page in wired:
        found[drawing_set, page].add(port)
    return {page: frozenset(ports) for page, ports in found.items()}


def end_boxes(
    geometry: SymbolGeometry,
    drawn: DrawnFunction,
    texts: PageTexts,
    facing: Facing,
    profile: Profile,
) -> list[Box]:
    """S16, Room's N or S call: the box of each of `drawn`'s texts at a `facing` port."""
    found = []
    for one in texts.owned.get(drawn.function, ()):
        own = symbol_port(drawn, one.port, geometry)
        port = leave_port(one.leave, own, geometry.ports, drawn, texts.wired)
        if port.facing is facing:
            found.append(_reserved(one, port, profile, texts))
    return found


def _reserved(one: MarkerDecision, at: PortGeometry, profile: Profile, texts: PageTexts) -> Box:
    """`_reserved_box` for a text at its port `at`, on the page `texts` holds."""
    tier = start_tier(star=one.star, joined=one.port in texts.joined, escaped=one.run is not None)
    return _reserved_box(one, at.at, at.facing, profile, tier=tier)


def reach_at(
    geometry: SymbolGeometry,
    drawn: DrawnFunction,
    texts: PageTexts,
    port: PortGeometry,
    profile: Profile,
) -> int:
    """S20 M9: how far the texts standing at `port` reach out along its facing, 0 for none."""
    far = 0
    for one in texts.owned.get(drawn.function, ()):
        own = symbol_port(drawn, one.port, geometry)
        at = leave_port(one.leave, own, geometry.ports, drawn, texts.wired)
        if at.name == port.name:
            box = _reserved(one, at, profile, texts)
            far = max(
                far, box.y + box.height - at.at.y if port.facing is Facing.S else at.at.y - box.y
            )
    return far


def symbol_port(drawn: DrawnFunction, port: Id[Any], geometry: SymbolGeometry) -> PortGeometry:
    """The port of `geometry`, the symbol `drawn` is placed with, that model port `port` is at."""
    name = next((one.symbol_port for one in drawn.ports if one.port == port), None)
    found = next((one for one in geometry.ports if one.name == name), None)
    if found is None:
        msg = "a port of a cut is not drawn at a port of the symbol its function is placed with"
        raise LayoutError(msg)
    return found


def leave_port(
    leave: Leave,
    own: PortGeometry,
    ports: tuple[PortGeometry, ...],
    drawn: DrawnFunction | None,
    wired: frozenset[Id[Any]],
) -> PortGeometry:
    """The symbol port a text stands at: `own` moved as `leave` says (C22, R7 B4, layout-0053)."""
    match leave:
        case Leave.PORT:
            return own
        case Leave.NORTH:
            return _facing(own, ports, Facing.N)
        case Leave.SOUTH:
            return _facing(own, ports, Facing.S)
    free = _free(ports, drawn, wired)
    if len(free) == 1:
        return _facing(own, ports, free[0])
    if leave is Leave.FREE_OR_PORT or own.facing is not Facing.N:
        return own
    return _facing(own, ports, Facing.S)


def _facing(own: PortGeometry, ports: tuple[PortGeometry, ...], facing: Facing) -> PortGeometry:
    """`own` when it faces `facing`, else the symbol's first port facing so, else `own`."""
    if own.facing is facing:
        return own
    return next((port for port in ports if port.facing is facing), own)


def _free(
    ports: tuple[PortGeometry, ...], drawn: DrawnFunction | None, wired: frozenset[Id[Any]]
) -> tuple[Facing, ...]:
    """C22: a terminal's N and S facings whose model port has no wire drawn; none for another."""
    if drawn is None or not drawn.roles.terminal:
        return ()
    by_symbol = {port.symbol_port: port.port for port in drawn.ports}
    facing_of = {g.facing: by_symbol.get(g.name) for g in ports}
    return tuple(f for f in (Facing.N, Facing.S) if f in facing_of and facing_of[f] not in wired)


def along(one: MarkerDecision, facing: Facing) -> int:
    """How far past its stub's home the text stands: `out` along an N or S stub, else none."""
    return one.out if facing in (Facing.N, Facing.S) else 0


def vertical(one: MarkerDecision, facing: Facing) -> bool:
    """S20 M1 (model-0114): `one`'s text reads along its wire, turned, at an N or S port."""
    return reads_along(one.run, facing)


def candidate_box(one: MarkerDecision, at: Point, facing: Facing) -> Box:
    """S2: `one`'s box at its first-ranked candidate beside its port at `at`, facing `facing`."""
    kind = TextKind.STUB if one.star == "off" else TextKind.REFERENCE
    width, height = one.size
    size = (height, width) if vertical(one, facing) else one.size
    first = ranked_candidates(kind, facing, size, DEFAULT_TABLE)[0]
    return box_of(dataclasses.replace(first, out=along(one, facing)), stub_anchor(at), size)


PIN_PITCH = 3 * WIRING_GRID  # the distance between two pins: the pole pitch


def run_box(
    first: Box, ends: tuple[Point, Point], content_width: int, text: str, profile: Profile
) -> tuple[Box, int | None]:
    """S20 M8, S14: a C21 run's one box over its pins, and where its text breaks (D14 M2)."""
    pad, height = 2 * profile.marker_padding, profile.text_height
    stubs = (ends[0].x, ends[1].x)
    north = first.y + first.height <= ends[0].y

    def need(line: str) -> int:
        return text_width(line, height=height) + pad

    width = max(2 * PIN_PITCH, stubs[1] - stubs[0] + PIN_PITCH)
    words = text.split(" ")
    wrap_at = None
    if need(text) > width:
        splits = [(" ".join(words[:k]), " ".join(words[k:]), k) for k in range(1, len(words))]
        fits = [k for one, two, k in splits if need(one) <= width and need(two) <= width]
        if fits:
            wrap_at = max(fits)
        elif splits:
            wrap_at = min(splits, key=lambda s: (max(need(s[0]), need(s[1])), -s[2]))[2]
            width = max(need(" ".join(words[:wrap_at])), need(" ".join(words[wrap_at:])))
        else:
            width = need(text)
    left = (stubs[0] + stubs[1]) // 2 - width // 2
    box = Box(
        x=left, y=first.y - (height if north else 0), width=width, height=first.height + height
    )
    return stand_against_content_edge(box, stubs, content_width) or box, wrap_at


def _text_box(one: MarkerDecision, at: Point, facing: Facing, profile: Profile) -> Box:
    """`candidate_box` with a merged stub's line (S5): the whole box the text takes."""
    box = candidate_box(one, at, facing)
    if one.merge is None:
        return box
    return merged(box, at, one.merge, profile, vertical=vertical(one, facing))[0]


def star_turns(star: str, *, terminal: bool) -> bool:
    """layout-0053: a `star` reference, or a non-terminal's off stub, turns where a wire ends."""
    return star == "ref" or (star == "off" and not terminal)


def start_tier(*, star: str, joined: bool, escaped: bool) -> int:
    """The tier a text's row starts at: 1 for a star text at a `joined` port, else 0."""
    return 1 if star and joined and not escaped else 0


def out_dir(*, south: bool) -> int:
    """The y sign of "out" from a port: +1 (down) for a south facing, -1 (up) for a north one."""
    return 1 if south else -1


def tier_offset(tier: int, height: int, *, south: bool) -> int:
    """The signed y step of `tier` box lengths out: down for a south facing, else up."""
    return tier * height * out_dir(south=south)


def _reserved_box(
    one: MarkerDecision, at: Point, facing: Facing, profile: Profile, *, tier: int
) -> Box:
    """S20 I4 Q1, M4: the box Room reserves for `one` at `at`, `start_tier` boxes out."""
    box = _text_box(one, at, facing, profile)
    return dataclasses.replace(
        box, y=box.y + tier_offset(tier, box.height, south=facing is Facing.S)
    )


def joined_ports(
    connections: tuple[Connection, ...], columns: tuple[Column, ...]
) -> frozenset[Id[Any]]:
    """The model ports whose connection runs to a side element's cell (S20 I4 Q1)."""
    sides = {cell.function for column in columns for cell in column.cells if cell.side}
    return frozenset(
        end.port
        for c in connections
        for end, other in ((c.a, c.b), (c.b, c.a))
        if other.function in sides
    )


def joined_box(boxes: tuple[Box, ...], at: Point, profile: Profile, *, vertical: bool) -> Box:
    """S20 M3: the one box of the markers at one pin, from `boxes` (each its own text's box)."""
    first, trim = boxes[0], 2 * profile.marker_padding * (len(boxes) - 1)
    if vertical:
        width, length = sum(b.width for b in boxes) - trim, max(b.height for b in boxes)
        north = first.y + first.height <= at.y
        y = first.y + first.height - length if north else first.y
        return Box(x=first.x + (first.width - width) // 2, y=y, width=width, height=length)
    height, width = sum(b.height for b in boxes) - trim, max(b.width for b in boxes)
    x = first.x if first.x >= at.x else first.x + first.width - width
    return Box(x=x, y=first.y + (first.height - height) // 2, width=width, height=height)


def merged(
    box: Box, at: Point, end_text: StubText, profile: Profile, *, vertical: bool = False
) -> tuple[Box, str]:
    """D9 (F7), S5: a reference's `box` at port `at` with one more line, the stub of `end_text`."""
    north = box.y + box.height <= at.y
    text = off_stub_line(end_text.cable, north=north, far=end_text.far, ports=[end_text.port])
    height = profile.text_height
    if vertical:
        length = max(box.height, text_width(text, height=height) + 2 * profile.marker_padding)
        width = box.width + height
        y = box.y + box.height - length if north else box.y
        return Box(x=box.x + (box.width - width) // 2, y=y, width=width, height=length), text
    width = max(box.width, text_width(text, height=height) + 2 * profile.marker_padding)
    if at.y <= box.y or box.y + box.height <= at.y:  # N or S: centred on the stub
        x = box.x + (box.width - width) // 2
        y = box.y if box.y >= at.y else box.y - height
    else:  # beside the port, growing about its middle
        x = box.x if box.x >= at.x else box.x + box.width - width
        y = box.y - height // 2
    return Box(x=x, y=y, width=width, height=box.height + height), text
