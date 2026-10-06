"""S9, D1 step 5: `texts` builds every reference and stub marker from its decision and the page.

`references` decides each text (`MarkerDecision`, no coordinate). Here it gets its geometry
from the placed cells: the port it stands at as placed (its `Leave`, `stand.leave_port`), its
box at its first candidate beside that port (`stand.candidate_box`, `out` further along an N or
S stub: S14's `further`), a merged stub's line (S5,
`stand.merged`), and a C21 run's one box across its placed ends (S14). Nothing before `texts`
builds a `LinkMarker`.
"""

from collections import defaultdict
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import (
    Facing,
    Point,
    port_page_at,
)
from fransys_layout.stages.references.types import Leave
from fransys_layout.stages.types import LinkMarker, PortRef

from .stand import (
    along,
    candidate_box,
    leave_port,
    merged,
    run_box,
    symbol_port,
    vertical,
    wired_by_page,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.geometry import PortGeometry
    from fransys_layout.stages.references.types import MarkerDecision, Page
    from fransys_layout.stages.types import (
        DrawnFunction,
        Handle,
        PlacedFunction,
        Profile,
        SheetFormat,
        StubText,
    )
    from fransys_model.kernel import Id

    from .stand import Wired


@dataclass(frozen=True, slots=True)
class LinkEnd:
    """One end of a text as placed: a port on a page, where it is drawn there, its facing."""

    ref: PortRef
    page: Page
    at: Point
    facing: Facing


@dataclass(frozen=True, slots=True)
class PlacedWorld:
    """What a marker is built on: each function's placement by page, and its drawing."""

    where: dict[Handle, dict[Page, PlacedFunction]]
    drawn_of: dict[Handle, DrawnFunction]


def placed_world(
    placed: tuple[PlacedFunction, ...], drawn: tuple[DrawnFunction, ...]
) -> PlacedWorld:
    """The placements of `placed` by function and page, and `drawn` by function."""
    where: dict[Handle, dict[Page, PlacedFunction]] = defaultdict(dict)
    for one in placed:
        where[one.function][one.drawing_set, one.page] = one
    return PlacedWorld(where=dict(where), drawn_of={one.function: one for one in drawn})


def link_markers(
    decisions: tuple[MarkerDecision, ...],
    world: PlacedWorld,
    *,
    wired: Wired,
    sheet: SheetFormat,
    profile: Profile,
) -> tuple[LinkMarker, ...]:
    """S9: the marker of every decision, in order, on the placed page (C21, C22, layout-0053)."""
    on_page = wired_by_page(wired)
    built = []
    for one in decisions:
        page = (one.drawing_set, one.page)
        end = link_end(PortRef(function=one.function, port=one.port), page, world)
        end = _leave(end, one.leave, world, on_page)
        marker = LinkMarker(
            connection=one.connection,
            port=one.port,
            side=one.side,
            drawing_set=one.drawing_set,
            page=one.page,
            at=end.at,
            box=candidate_box(one, end.at, end.facing),
            partner_page=one.partner_page,
            stub_extra=along(one, end.facing),
            star=one.star,
            star_partner=one.partner if one.star else None,
            star_partner_set=one.partner_set if one.star else 0,
            text=one.text,
            end_text=one.end_text,
            vertical=vertical(one, end.facing),
            symbol=one.symbol,
            symbol_text=one.symbol_text,
        )
        built.append(marker if one.merge is None else _with_off(marker, one.merge, profile))
    return _with_runs(built, decisions, sheet, profile)


def _leave(
    end: LinkEnd, leave: Leave, world: PlacedWorld, on_page: Mapping[Page, frozenset[Id[Any]]]
) -> LinkEnd:
    """`end` moved to the port `leave` names, as placed (`stand.leave_port`)."""
    if leave is Leave.PORT:
        return end
    placement = world.where[end.ref.function][end.page]
    own = _symbol_port(end.ref, placement, world)
    ports = placement.geometry.ports
    drawn = world.drawn_of.get(end.ref.function)
    port = leave_port(leave, own, ports, drawn, on_page.get(end.page, frozenset()))
    if port is own:
        return end
    at = port_page_at(placement.at, port)
    return LinkEnd(ref=end.ref, page=end.page, at=at, facing=port.facing)


def link_end(ref: PortRef, page: Page, world: PlacedWorld) -> LinkEnd:
    """A port's position on `page`, where its function is placed."""
    placement = world.where[ref.function][page]
    port = _symbol_port(ref, placement, world)
    return LinkEnd(ref=ref, page=page, at=port_page_at(placement.at, port), facing=port.facing)


def _symbol_port(ref: PortRef, placement: PlacedFunction, world: PlacedWorld) -> PortGeometry:
    """The port of `placement`'s symbol that `ref` is drawn at (`stand.symbol_port`)."""
    return symbol_port(world.drawn_of[ref.function], ref.port, placement.geometry)


def _with_off(ref: LinkMarker, end_text: StubText, profile: Profile) -> LinkMarker:
    """D9 (F7), S5: the reference marker `ref` with one more line, the off stub of `end_text`."""
    box, text = merged(ref.box, ref.at, end_text, profile, vertical=ref.vertical)
    return replace(ref, box=box, text=text)


def _with_runs(
    built: Sequence[LinkMarker],
    decisions: tuple[MarkerDecision, ...],
    sheet: SheetFormat,
    profile: Profile,
) -> tuple[LinkMarker, ...]:
    """S14: each C21 run's one box across its placed stubs (`stand.run_box`, S20 M8)."""
    members: dict[int, list[int]] = defaultdict(list)
    for index, one in enumerate(decisions):
        if one.run is not None:
            members[one.run].append(index)
    found = list(built)
    for indices in members.values():
        first, last = found[indices[0]], found[indices[-1]]
        box, wrap_at = run_box(
            first.box, (first.at, last.at), sheet.content_width, first.text, profile
        )
        for rank, index in enumerate(indices):
            found[index] = replace(
                found[index], box=box, shared_box=True, lead=rank == 0, wrap_at=wrap_at
            )
    return tuple(found)


def wired_points(
    placed: tuple[PlacedFunction, ...],
    drawn: tuple[DrawnFunction, ...],
    wired: Wired,
) -> frozenset[tuple[int, int, int, int]]:
    """`(set, page, x, y)` of every symbol port whose model port `wired` holds (layout-0053)."""
    model_port = {(one.function, p.symbol_port): p.port for one in drawn for p in one.ports}
    found = set()
    for one in placed:
        for g in one.geometry.ports:
            if (model_port.get((one.function, g.name)), one.drawing_set, one.page) in wired:
                at = port_page_at(one.at, g)
                found.add((one.drawing_set, one.page, at.x, at.y))
    return frozenset(found)
