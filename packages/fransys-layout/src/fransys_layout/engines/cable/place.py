"""The cable engine's placer: a block's facts to its geometry, in G from its corner (CD8)."""

lazy from collections.abc import Sequence

from fransys_layout.engines.cable.channel import Plan, plan_channel, rise
from fransys_layout.engines.cable.place_frame import (
    Spans,
    box_room,
    box_top,
    boxes_fit,
    cable_boxes,
    dash_top,
    dashed_box,
    spans,
)
from fransys_layout.engines.cable.place_links import (
    Line,
    lift,
    link_wires,
    links_of,
    lower,
    upper_lines,
)
from fransys_layout.engines.cable.place_rows import row_xs
from fransys_layout.engines.cable.route import Band, route_lower
from fransys_layout.engines.cable.values import (
    BlockFacts,
    CoreFacts,
    EndFacts,
    PlacedBlock,
    PlacedCable,
    PlacedCell,
    PlacedEnd,
    PlacedWire,
)
from fransys_layout.geometry import PORT_PITCH_G, WIRING_GRID, Box, LayoutError, Point, snap_up
from fransys_layout.stages.space import Obstacle

G = WIRING_GRID
ROW = 2 * G  # label room, end-box height and the band between an end box and the cable box
STUB = G  # the stub of a blank end (CD11)


def block_pitch(widest: int) -> int:
    """The pitch rule: `widest` plus one grid unit, rounded up to whole pin pitches (CD8)."""
    return snap_up(widest + G, grid=PORT_PITCH_G)


def _cores(facts: BlockFacts) -> tuple[CoreFacts, ...]:
    """Every core of the block that crosses between the rows, cable by cable in print order."""
    return tuple(core for cable in facts.cables for core in cable.cores if not core.link)


def _widest(facts: BlockFacts) -> int:
    pins = (pin.marking_width for end in (*facts.top, *facts.bottom) for pin in end.pins)
    return max(pins, default=0)


def _spans(facts: BlockFacts, ends: tuple[PlacedEnd, ...]) -> Spans:
    """Each cable's top columns (first, last), from the placed rows."""
    owners = tuple(n for n, cable in enumerate(facts.cables) for c in cable.cores if not c.link)
    tops = tuple(top[0] for _, top, _ in _landings(facts, ends))
    return spans(owners, tops, len(facts.cables))


def _pitch(facts: BlockFacts) -> int:
    """The block pitch; a harness grows it by whole pin pitches until each heading fits (Q2)."""
    pitch = block_pitch(_widest(facts))
    while facts.harness_width is not None and not boxes_fit(
        facts, _spans(facts, _place_rows(facts, 0, pitch, 2 * G)[0]), pitch
    ):
        pitch += PORT_PITCH_G
    return pitch


def _overhang(end: EndFacts, pitch: int) -> int:
    return max(0, -(-(end.label_width - len(end.pins) * pitch) // 2))


def _origin(facts: BlockFacts, pitch: int) -> int:
    drawn = (row[0] for row in (facts.top, facts.bottom) if row and not row[0].blank)
    return snap_up(max((_overhang(end, pitch) for end in drawn), default=0))


def _top_y(end: EndFacts, rise_by: int) -> tuple[int, int]:
    """The end box's y and the cable box's y of a top row; its links lift the box by `rise_by`."""
    if end.blank:
        return 0, STUB
    return ROW, 3 * ROW + rise_by


def _place_end(end: EndFacts, x0: int, pitch: int, y: int, *, top: bool) -> PlacedEnd:
    """One end box with its left edge at `x0`; its pin cells step one pitch from half a pitch in."""
    cells = tuple(
        PlacedCell(port=pin.port, x=x0 + pitch // 2 + i * pitch, landed=pin.landed)
        for i, pin in enumerate(end.pins)
    )
    return PlacedEnd(
        item=end.item,
        top=top,
        dashed=end.dashed,
        blank=end.blank,
        x=x0,
        y=y,
        width=len(end.pins) * pitch,
        height=0 if end.blank else ROW,
        cells=cells,
    )


def _place_row(
    row: tuple[EndFacts, ...], x0: int, pitch: int, y: int, *, top: bool
) -> tuple[PlacedEnd, ...]:
    """One row's end boxes at height `y`, packed left to right (a row is all drawn or all blank)."""
    if len({end.blank for end in row}) > 1:
        message = "a cable block row holds drawn ends or blank ends, never both"
        raise LayoutError(message)
    xs = row_xs(row, x0, pitch)
    return tuple(_place_end(end, x, pitch, y, top=top) for end, x in zip(row, xs, strict=True))


def _place_rows(
    facts: BlockFacts, x0: int, pitch: int, drop: int
) -> tuple[tuple[PlacedEnd, ...], int, int]:
    """The placed ends, the cable box's y and the block's height.

    `drop` is the height between the box and a drawn bottom row: its tracks (CT5-3). The upper
    band grows for the top row's links (CD8 at L1).
    """
    end_y = _top_y(facts.top[0], 0)[0] if facts.top else 0
    top = _place_row(facts.top, x0, pitch, end_y, top=True)
    box_y = _top_y(facts.top[0], lift(facts, top))[1] if facts.top else 0
    harness = facts.harness_width is not None
    if harness:
        box_y = box_top(facts, box_y)
    below = box_y + box_room(facts)[0] + (G if harness else 0)
    if not facts.bottom:
        return top, box_y, below
    blank = facts.bottom[0].blank
    end_y = below + (STUB if blank else drop)
    bottom = _place_row(facts.bottom, x0, pitch, end_y, top=False)
    return (*top, *bottom), box_y, end_y + (0 if blank else 2 * ROW)


type Landing = tuple[bool, tuple[int, PlacedEnd], tuple[int, PlacedEnd]]


def _landings(facts: BlockFacts, ends: tuple[PlacedEnd, ...]) -> list[Landing]:
    """Per core: whether `end_a` is the top end, then its top and bottom landing as (x, end)."""
    where = {cell.port: (cell.x, end) for end in ends for cell in end.cells}
    found = []
    for core in _cores(facts):
        a, b = where[core.end_a], where[core.end_b]
        found.append((True, a, b) if a[1].top else (False, b, a))
    return found


def _columns(
    facts: BlockFacts,
    landings: Sequence[tuple[bool, tuple[int, PlacedEnd], tuple[int, PlacedEnd]]],
) -> list[tuple[int, int, int]]:
    """Each core's key, top x and bottom x; a blank bottom row takes the column (a stub)."""
    return [
        (core.key, top[0], top[0] if bottom[1].blank else bottom[0])
        for core, (_, top, bottom) in zip(_cores(facts), landings, strict=True)
    ]


def _band(facts: BlockFacts, ends: tuple[PlacedEnd, ...], boxes: tuple[Box, ...], top: int) -> Band:
    """The lower band: from `top` down to the bottom row; the cable boxes and that row close it."""
    drawn = [
        Box(x=e.x, y=e.y, width=e.width, height=e.height) for e in ends if not e.top and not e.blank
    ]
    return Band(
        top=top,
        obstacles=tuple(Obstacle(box=b, lanes=()) for b in (*boxes, *drawn)),
        turn_penalty=facts.turn_penalty,
        crossing_penalty=facts.crossing_penalty,
        head=facts.text_height,
    )


def _wires(
    facts: BlockFacts, ends: tuple[PlacedEnd, ...], box_y: int, plan: Plan, band: Band
) -> tuple[PlacedWire, ...] | None:
    """Each core's two runs: a straight drop in the upper band, the routed lower run (CD8).

    A row link keeps its row (`place_links`); a bottom-row link is routed with the lower cores.
    """
    landings = _landings(facts, ends)
    below = box_y + box_room(facts)[0]
    pairs = [
        (Point(x=top[0], y=below), Point(x=top[0] if bottom[1].blank else bottom[0], y=bottom[1].y))
        for _, top, bottom in landings
    ]
    cores, links = _cores(facts), links_of(facts, ends)
    low = lower(links)
    keys = [core.key for core in cores] + [link.core.key for link in low]
    lowers = route_lower(pairs + [link.pins for link in low], keys, plan, band)
    if lowers is None:
        return None
    lines = upper_lines(facts, links)
    lines |= {k.core.key: line for k, line in zip(low, lowers[len(cores) :], strict=True)}
    built = [
        _core_wire(facts, box_y, core, landing, run)
        for core, landing, run in zip(cores, landings, lowers[: len(cores)], strict=True)
    ]
    drawn = [run for _, runs in built for run in runs]
    return (*(wire for wire, _ in built), *link_wires(facts, links, lines, drawn))


def _core_wire(
    facts: BlockFacts, box_y: int, core: CoreFacts, landing: Landing, lower_run: Line
) -> tuple[PlacedWire, tuple[Line, Line]]:
    """One crossing core's record, and its upper and lower runs."""
    a_top, top, bottom = landing
    upper = (Point(x=top[0], y=top[1].y + top[1].height), Point(x=top[0], y=box_y))
    down, up = (upper, lower_run[::-1]) if a_top else (lower_run, upper[::-1])
    wire = PlacedWire(
        conductor=core.conductor,
        run_a=down,
        run_b=up,
        text_x=top[0],
        text_y=box_y + box_room(facts)[1],
        stub_a=(top if a_top else bottom)[1].blank,
        stub_b=(bottom if a_top else top)[1].blank,
    )
    return wire, (upper, lower_run)


def _box_width(facts: BlockFacts, ends: tuple[PlacedEnd, ...]) -> int:
    """As wide as the top row, so its pin columns stand in the box; wider for a bottom box."""
    tops = [e for e in ends if e.top]
    bottoms = [e.width for e in ends if not e.top]
    row = max((e.x + e.width for e in tops), default=0) - min((e.x for e in tops), default=0)
    return snap_up(max(facts.cables[0].heading_width + 2 * facts.pad, row, *bottoms))


def _frame(
    facts: BlockFacts, ends: tuple[PlacedEnd, ...], pitch: int, x0: int, box_y: int
) -> tuple[tuple[PlacedCable, ...], Box | None] | None:
    """The cable boxes and the dashed box: one lone box over the top row, or the harness frame."""
    if facts.harness_width is None:
        box = Box(x=x0, y=box_y, width=_box_width(facts, ends), height=box_room(facts)[0])
        return (
            PlacedCable(cable=facts.cables[0].cable, external=facts.cables[0].external, box=box),
        ), None
    boxes = cable_boxes(facts, _spans(facts, ends), pitch, box_y, x0)
    label = (facts.harness_width or 0) + 2 * facts.pad
    if boxes is None:
        return None
    tops = [top[0] for _, top, _ in _landings(facts, ends)]
    return boxes, dashed_box(
        label, boxes, min(tops, default=None), dash_top(_top_y_of(facts, ends))
    )


def _top_y_of(facts: BlockFacts, ends: tuple[PlacedEnd, ...]) -> int:
    return _top_y(facts.top[0], lift(facts, ends))[1] if facts.top else 0


def _right(
    facts: BlockFacts,
    ends: tuple[PlacedEnd, ...],
    boxes: tuple[Box, ...],
    wires: Sequence[PlacedWire],
) -> int:
    labels = {e.item: e.label_width for e in (*facts.top, *facts.bottom) if not e.blank}
    edges = [b.x + b.width for b in boxes]
    edges += [end.x + end.width for end in ends]
    edges += [end.x + (end.width + labels[end.item] + 1) // 2 for end in ends if not end.blank]
    wide = {c.conductor: c.text_width for cable in facts.cables for c in cable.cores if c.link}
    edges += [w.text_x + (wide[w.conductor] + 1) // 2 for w in wires if w.conductor in wide]
    return snap_up(max(edges))


def _plan(facts: BlockFacts, pitch: int) -> Plan | None:
    ends = _place_rows(facts, _origin(facts, pitch), pitch, 2 * G)[0]
    low = lower(links_of(facts, ends))
    columns = [*_columns(facts, _landings(facts, ends)), *((k.core.key, k.a, k.b) for k in low)]
    return plan_channel(columns, {link.core.key for link in low})


def _place_at(
    facts: BlockFacts, pitch: int, x0: int, tracks: int, plan: Plan
) -> PlacedBlock | None:
    drop = rise(plan, tracks, facts.text_height) + G
    ends, box_y, height = _place_rows(facts, x0, pitch, drop)
    frame = _frame(facts, ends, pitch, x0, box_y)
    if frame is None:
        return None
    boxes, harness = frame
    shape = [placed.box for placed in boxes]
    band = _band(facts, ends, tuple(shape), box_y + box_room(facts)[0] + (G if harness else 0))
    wires = _wires(facts, ends, box_y, plan, band)
    if wires is None:
        return None
    edges = [*shape, *([harness] if harness else [])]
    return PlacedBlock(
        subject=facts.subject,
        unit=facts.unit,
        sheet_format=facts.sheet_format,
        width=_right(facts, ends, tuple(edges), wires),
        height=height,
        pitch=pitch,
        boxes=boxes,
        harness=harness,
        ends=ends,
        wires=wires,
    )


def place_tracks(facts: BlockFacts, tracks: int) -> PlacedBlock | None:
    """The block with `tracks` tracks in its lower band, or None when its cores need more."""
    pitch = _pitch(facts)
    plan = _plan(facts, pitch)
    if plan is None or plan.count > tracks:
        return None
    x0 = _origin(facts, pitch)
    block = _place_at(facts, pitch, x0, tracks, plan)
    if block is not None and block.harness is not None and block.harness.x < 0:
        block = _place_at(facts, pitch, x0 + snap_up(-block.harness.x), tracks, plan)
    return block


def place_block(facts: BlockFacts) -> PlacedBlock | None:
    """Return the geometry of one block, or None when its cores cannot be routed.

    The lower band holds as many tracks as the channel needs, at least one (CT5-3 P2 ruling).
    """
    plan = _plan(facts, _pitch(facts))
    return None if plan is None else place_tracks(facts, max(1, plan.count))
