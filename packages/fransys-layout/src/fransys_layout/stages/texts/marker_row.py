"""S20 (layout-0090): each page's link markers placed by D3's placer, the page's first texts.

settle's four marker moves are the row's places and the placer's rules (S20, ruled after Part
4b's stop):

- `further` (I4 Q1): a star marker at a port a side element joins starts one tier out, one box
  height (S14's n-th-out candidate).
- `turned` (layout-0053): a star reference where a wire ends on its point has one place, the
  turned box (`tidy.turned`): every place over the wired point is not free.
- the stagger (R7 B4): the greedy walk to the next free place, tier by tier.
- WIRE-X56: no place covers a port's lane (`_lanes`): a sibling's that runs the box's way, or
  any port's that faces the box from beyond it, the marker's own port exempt, not its
  function's other ports; a moved place stays one grid clear of it.

A row, tier by tier (every place of tier n before tier n+1), a tier one box height out: the home
over the stub, then sideways steps with the stub still over the box (half a grid of margin,
layout-0054), among them the box against a content edge, growing away from it (D14 M2,
layout-0068). A place beyond a lane with a lead (layout-0054) comes after the last tier. A row
holds only places a record can draw: a moved box is `shared_box` and `lead` (a plain rectangle
where it stands), an arrow box is centred on its port, and a turned marker, a C21 run's box and
a box beside an E or W port have one place each.

The call is bounded by the unshifted content box along x, as settle's clamp was (C22b's shift
never measures a marker, D14 M2). The tiers end where the box leaves the content box or meets
another function's body: the room (S14, S16), not a constant.
"""

from collections import defaultdict
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import WIRING_GRID, Box, Facing, Point, follow
from fransys_layout.stages.labels import decided_runs
from fransys_layout.stages.tidy import turned

from .candidates import TextKind
from .clear_bodies import place_clear_of_bodies
from .marker_lanes import FAR, Lane, Reach, lanes_of, meets_lane, on_lane, reach_of
from .markers import wired_points
from .place_texts import Place, TextToPlace
from .stand import joined_box, joined_ports, star_turns, start_tier, tier_offset

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.stages.types import DrawnFunction, LinkMarker, PlacedFunction, Profile
    from fransys_model.kernel import Finding, Id

    from .marker_room import MarkerRoom

_MARGIN = WIRING_GRID // 2  # layout-0054: a stub stands half a grid inside its box


@dataclass(frozen=True, slots=True)
class _Page:
    """What a page's rows read: its lanes, each port's function, the sheet's content box."""

    lanes: tuple[Lane, ...]
    owner: dict[Id[Any], Id[Any]]
    joined: frozenset[Id[Any]]
    wired_at: frozenset[tuple[int, int, int, int]]
    width: int
    height: int
    profile: Profile
    terminals: frozenset[Id[Any]] = frozenset()


def place_markers(
    markers: tuple[LinkMarker, ...],
    placed: tuple[PlacedFunction, ...],
    drawn: tuple[DrawnFunction, ...],
    around: MarkerRoom,
) -> tuple[tuple[LinkMarker, ...], tuple[Finding, ...]]:
    """S20: every marker of `markers` at the first free place of its row, page by page (M3)."""
    model_port = {(one.function, p.symbol_port): p.port for one in drawn for p in one.ports}
    base = _Page(
        lanes=(),
        owner={port.port: one.function for one in drawn for port in one.ports},
        joined=joined_ports(around.connections, around.columns),
        wired_at=wired_points(placed, drawn, around.wired),
        width=around.sheet.content_width,
        height=around.sheet.content_height,
        profile=around.profile,
        terminals=frozenset(one.function for one in drawn if one.roles.terminal),
    )
    on_page = _by_page(placed)
    found, findings = dict(enumerate(markers)), ()
    for page, indices in _by_page(markers).items():
        here = tuple(placed[i] for i in on_page.get(page, ()))
        room = replace(base, lanes=lanes_of(here, model_port))
        decided = _decided(here, drawn, around, page)
        written, page_findings = _place_page(markers, indices, here, room, decided)
        found.update(written)
        findings += page_findings
    return tuple(found.values()), findings


def _by_page(items: Sequence[Any]) -> dict[tuple[int, int], list[int]]:
    """The indices of `items` on each (drawing set, page), in order."""
    pages: dict[tuple[int, int], list[int]] = defaultdict(list)
    for index, one in enumerate(items):
        pages[one.drawing_set, one.page].append(index)
    return pages


def _place_page(
    markers: tuple[LinkMarker, ...],
    indices: Sequence[int],
    here: tuple[PlacedFunction, ...],
    room: _Page,
    decided: tuple[Box, ...],
) -> tuple[dict[int, LinkMarker], tuple[Finding, ...]]:
    """One page's markers placed by the placer: the records that moved and the findings."""
    runs = _runs(markers, indices)
    # C21: a run's first member stands for all of them; M3: markers at one pin are one text
    standing = [i for i in indices if not markers[i].shared_box or runs[markers[i].box][0] == i]
    mates = _pin_mates(markers, standing, room)
    stand = _stand(markers, mates, room.profile)
    standing = [i for i in standing if not any(i in rest for rest in mates.values())]
    rows = _rows(stand, standing, runs, markers, room)
    content = Box(x=0, y=-FAR, width=room.width, height=2 * FAR)
    texts = _texts(stand, standing, rows, room.owner)
    done, findings = place_clear_of_bodies(texts, rows, here, decided, content)
    return _written(done, rows, markers, mates), findings


def _decided(
    here: tuple[PlacedFunction, ...],
    drawn: tuple[DrawnFunction, ...],
    around: MarkerRoom,
    page: tuple[int, int],
) -> tuple[Box, ...]:
    """S20: the decided runs no text stands on (a C23 corridor, a joined run's wire)."""
    joins = tuple(run for run in around.joins if (run.drawing_set, run.page) == page)
    return decided_runs(here, drawn, around.connections, joins)


def _runs(markers: tuple[LinkMarker, ...], indices: Sequence[int]) -> dict[Box, list[int]]:
    """C21: a run's members share one box, its one place."""
    runs: dict[Box, list[int]] = defaultdict(list)
    for index in indices:
        if markers[index].shared_box:
            runs[markers[index].box].append(index)
    return runs


def _stand(
    markers: tuple[LinkMarker, ...], mates: Mapping[int, list[int]], profile: Profile
) -> list[LinkMarker]:
    """The markers, each pin's first one with the box that holds all its mates."""
    stand = list(markers)
    for lead, rest in mates.items():
        one = markers[lead]
        boxes = tuple(markers[i].box for i in (lead, *rest))
        stand[lead] = replace(one, box=joined_box(boxes, one.at, profile, vertical=one.vertical))
    return stand


def _rows(
    stand: Sequence[LinkMarker],
    standing: Sequence[int],
    runs: Mapping[Box, list[int]],
    markers: tuple[LinkMarker, ...],
    room: _Page,
) -> dict[int, list[tuple[LinkMarker, Place]]]:
    """Each standing marker's row; a run's first member has one place with every member's stub."""
    rows = {index: _row(stand[index], room) for index in standing}
    for run in runs.values():
        stubs = tuple(box for i in run for box in stub_boxes(markers[i]))
        lead = markers[run[0]]
        rows[run[0]] = [(lead, Place(box=lead.box, stub=stubs))]
    return rows


def _texts(
    stand: Sequence[LinkMarker],
    standing: Sequence[int],
    rows: Mapping[int, list[tuple[LinkMarker, Place]]],
    owner: Mapping[Id[Any], Id[Any]],
) -> tuple[TextToPlace, ...]:
    """The placer's text for each standing marker, its places the row's."""
    return tuple(
        TextToPlace(
            kind=TextKind.STUB if stand[index].star == "off" else TextKind.REFERENCE,
            handle=stand[index].port,
            slot=f"{index:06d}",
            position=stand[index].at,
            width=stand[index].box.width,
            height=stand[index].box.height,
            anchors=(),
            own=(owner[stand[index].port],) if stand[index].port in owner else (),
            places=tuple(place for _, place in rows[index]),
            rank=0 if len(rows[index]) == 1 or rows[index][0][0].turn is not None else 1,  # S20
        )
        for index in standing
    )


def _written(
    done: Sequence[Any],
    rows: Mapping[int, list[tuple[LinkMarker, Place]]],
    markers: tuple[LinkMarker, ...],
    mates: Mapping[int, list[int]],
) -> dict[int, LinkMarker]:
    """The record each placed text writes, and its mates' records sharing its box."""
    found: dict[int, LinkMarker] = {}
    for one in done:
        index = int(one.slot)
        found[index] = row = rows[index][one.index][0]
        for mate in mates.get(index, ()):
            found[mate] = replace(
                markers[mate],
                box=row.box,
                stub_extra=row.stub_extra,
                turn=row.turn,
                shared_box=True,
                lead=False,
            )
    return found


def _pin_mates(
    markers: tuple[LinkMarker, ...], indices: Sequence[int], room: _Page
) -> dict[int, list[int]]:
    """M3, S20 M7: each multi-marker pin's first marker, a turned reference first, others share."""
    at_pin: dict[Point, list[int]] = defaultdict(list)
    for index in indices:
        if not markers[index].shared_box:
            at_pin[markers[index].at].append(index)
    pins = (sorted(pin, key=lambda i: not _turns(markers[i], room)) for pin in at_pin.values())
    return {pin[0]: pin[1:] for pin in pins if len(pin) > 1}


def _turns(marker: LinkMarker, room: _Page) -> bool:
    """layout-0053: a star reference or off stub where a wire ends on its point is turned (M7)."""
    at = marker.at
    # a terminal's off stub stands at its free symbol port, which `wired_at` (by model port) holds
    kind = star_turns(marker.star, terminal=room.owner.get(marker.port) in room.terminals)
    return kind and (marker.drawing_set, marker.page, at.x, at.y) in room.wired_at


def stub_boxes(marker: LinkMarker) -> tuple[Box, ...]:
    """The boxes a marker's stub takes: port to box, or via a junction; lead: layout-0054."""
    at, box = marker.at, marker.box
    if marker.turn is not None:  # M7: port to the junction, the branch, the stub up to the box
        via, end = marker.turn, Point(x=box.x + box.width // 2, y=marker.turn.y)
        near = box.y + box.height if box.y < via.y else box.y
        return (corridor(at, via), corridor(via, end), corridor(end, Point(x=end.x, y=near)))
    north, south = box.y + box.height <= at.y, box.y >= at.y
    if not (north or south):  # beside an E or W port
        near = box.x if box.x >= at.x else box.x + box.width
        return (corridor(at, Point(x=near, y=at.y)),)
    near = box.y + box.height if north else box.y
    found = [corridor(at, Point(x=at.x, y=near))]
    if not box.x <= at.x <= box.x + box.width:
        edge = box.x if box.x > at.x else box.x + box.width
        found.append(corridor(Point(x=at.x, y=near), Point(x=edge, y=near)))
    return tuple(found)


def corridor(a: Point, b: Point) -> Box:
    """A two-wide box around the axis-aligned run from `a` to `b`, ends included."""
    x0, x1 = sorted((a.x, b.x))
    y0, y1 = sorted((a.y, b.y))
    return Box(x=x0 - 1, y=y0 - 1, width=x1 - x0 + 2, height=y1 - y0 + 2)


def _row(marker: LinkMarker, room: _Page) -> list[tuple[LinkMarker, Place]]:
    """The marker's places in order, each with the record it writes there (S20's row)."""
    at, box = marker.at, marker.box
    south, north = box.y >= at.y, box.y + box.height <= at.y
    if _turns(marker, room):
        # a lane on the pin's own x is its own wire's, whichever port stands there (M7)
        lanes = tuple(lane for lane in _lanes_beside(marker, room, south=south) if lane.x != at.x)
        return [_place(turned(marker, side), reach_of(lanes)) for side in (1, -1)]
    if marker.shared_box or not (south or north) or not box.x <= at.x <= box.x + box.width:
        return [_place(marker, ())]
    lanes = _lanes_beside(marker, room, south=south)
    start = start_tier(star=marker.star, joined=marker.port in room.joined, escaped=False)
    own = next(
        (
            lane
            for lane in room.lanes
            if lane.port == marker.port and lane.facing is (Facing.S if south else Facing.N)
        ),
        None,
    )
    reach = reach_of(lanes)
    tiers = follow(
        start, lambda t: t + 1 if _fits(_base(marker, t + 1, south=south), room, own) else None
    )
    row = [
        place
        for tier in tiers
        for place in _tier(_base(marker, tier, south=south), reach, room, home_closed=tier == 0)
    ]
    row.extend(_beyond(row[0][0], reach, room))
    return row


def _base(marker: LinkMarker, tier: int, *, south: bool) -> LinkMarker:
    """The marker `tier` box heights out from its home, its stub that much longer."""
    box = marker.box
    return replace(
        marker,
        box=replace(box, y=box.y + tier_offset(tier, box.height, south=south)),
        stub_extra=marker.stub_extra + tier * box.height,
    )


def _fits(base: LinkMarker, room: _Page, own: Lane | None) -> bool:
    """Whether a tier's box is in the content box and on its own lane: the walk goes on."""
    return _in_room(base, room) and _within_lane(base.box, own)


def _lanes_beside(marker: LinkMarker, room: _Page, *, south: bool) -> tuple[Lane, ...]:
    """The lanes a marker's box keeps clear of (its own port's lane is its own wire)."""
    toward, mine = (Facing.S if south else Facing.N), room.owner.get(marker.port)
    return tuple(
        lane
        for lane in room.lanes
        if lane.port != marker.port and (lane.facing is not toward or lane.function == mine)
    )


def _within_lane(box: Box, lane: Lane | None) -> bool:
    """S20 8b: a tier's box stays on its own port's lane, short of the next symbol on its line."""
    if lane is None:
        return True
    if lane.facing is Facing.S:
        return box.y + box.height <= lane.end
    return box.y >= lane.end


def _in_room(marker: LinkMarker, room: _Page) -> bool:
    """Whether a tier's box stays inside the content box, top to bottom (S14, S16)."""
    return marker.box.y >= 0 and marker.box.y + marker.box.height <= room.height


def _tier(
    base: LinkMarker, reach: tuple[Reach, ...], room: _Page, *, home_closed: bool
) -> list[tuple[LinkMarker, Place]]:
    """One tier's places: the home, then each sideways x with the stub over the box."""
    box, stub = base.box, base.at.x
    low, high = stub + _MARGIN - box.width, stub - _MARGIN
    steps = {box.x + k * _MARGIN for k in range(-box.width // _MARGIN, box.width // _MARGIN + 1)}
    steps |= {x + WIRING_GRID for x, _, _ in reach}
    steps |= {x - WIRING_GRID - box.width for x, _, _ in reach}
    steps |= {0, room.width - box.width}
    xs = sorted(
        (x for x in steps if low <= x <= high and x != box.x),
        key=lambda x: (abs(x - box.x), x < box.x),
    )
    home = _place(base, reach, clear=not home_closed)
    moved = [replace(base, box=replace(box, x=x), shared_box=True, lead=True) for x in xs]
    return [home, *(_place(one, reach, clear=True) for one in moved)]


def _beyond(
    first: LinkMarker, reach: tuple[Reach, ...], room: _Page
) -> list[tuple[LinkMarker, Place]]:
    """layout-0054: the places one grid clear beyond a lane from the stub, shortest lead first."""
    box, stub = first.box, first.at.x
    near = [lane for lane in reach if meets_lane(box, lane)]
    found = []
    for lane_x, _, _ in near:
        # the boxes of the pins in a row stand side by side beyond the lane: one more box width
        # out for each lane the box meets
        for k in range(len(near)):
            for x in (
                lane_x + WIRING_GRID + k * box.width,
                lane_x - WIRING_GRID - box.width - k * box.width,
            ):
                end = x + box.width
                between = any(x > one_x >= stub or end < one_x <= stub for one_x, _, _ in near)
                if between and 0 <= x <= room.width - box.width:
                    found.append((x - stub if x > stub else stub - end, x))
    south = box.y >= first.at.y
    moved = [
        replace(
            first,
            box=replace(box, x=x, y=box.y - dy if south else box.y + dy),
            stub_extra=first.stub_extra - dy,
            shared_box=True,
            lead=True,
        )
        for _, x in sorted(set(found))
        for dy in _closer(first, south=south)
    ]
    return [_place(one, reach, clear=True) for one in moved]


def _closer(marker: LinkMarker, *, south: bool) -> range:
    """How far a beyond-lane box may stand nearer its port, in grids: leads at other heights."""
    box, at = marker.box, marker.at
    stub = box.y - at.y if south else at.y - (box.y + box.height)
    return range(0, max(min(stub - WIRING_GRID, marker.stub_extra), 0) + 1, WIRING_GRID)


def _place(
    marker: LinkMarker, reach: tuple[Reach, ...], *, clear: bool = True
) -> tuple[LinkMarker, Place]:
    """The record and its `Place`: its box, its stub's boxes, and whether it is off every lane."""
    covered = any(on_lane(marker.box, lane, clear=clear) for lane in reach)
    return marker, Place(box=marker.box, stub=stub_boxes(marker), fits=not covered)
