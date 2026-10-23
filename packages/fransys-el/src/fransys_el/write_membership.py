"""The `layout.membership` rows of a core layout: where each function, port, end and item sits.

One row per subject per page: the frame cell of its place, its reading rank (`reading_ranks`)
and, for a port or conductor end, whether it is drawn there or only a reference marker (F7).
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fransys_layout.core import PinRef
from fransys_model.derive import build_indexes, frame_cell, function_item
from fransys_model.derive.order import reading_ranks
from fransys_model.kernel import make_id, render_id
from fransys_model.layout import FrameCell, Membership, Shown

from .kit_keys import function_of
from .placement_ids import pin_names, symbol_ids

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from fransys_layout.core import CoreLayout, Placed, PlacementProblem, Sym
    from fransys_model.kernel import Id, Model
    from fransys_model.layout import Page
    from fransys_model.vocab import Conductor, Port

    from .placement_kit import PickKey, SymbolKit

__all__ = ["memberships"]

_KEY = ("layout", "core", "membership")


@dataclass(frozen=True, slots=True)
class _Spot:
    """One subject at a place on a page: the `Membership` field it fills, its id and the place."""

    key: tuple[str, ...]
    field: str
    subject: Id[object]
    page: int
    at: tuple[int, int]
    shown: Shown | None = None


def _spot(
    ctx: _Ctx,
    field: str,
    subject: Id[object],
    place: tuple[int, tuple[int, int]],
    shown: Shown | None = None,
    *tag: str,
) -> _Spot:
    """The spot of `subject` at `place` (page number, (x, y)); page numbers restart in each set."""
    page, at = place
    key = (*_KEY, str(ctx.number), field, *tag, render_id(subject), str(page))
    return _Spot(key, field, subject, page, at, shown)


@dataclass(frozen=True, slots=True)
class _Ctx:
    """What the rows read: the model, each symbol's lead keys, ports and pin refs, the layout."""

    model: Model
    kit: SymbolKit
    syms: Mapping[str, Sym]
    leads: Mapping[str, list[PickKey]]
    pins: Mapping[str, list[tuple[Id[Port], str]]]
    ends: Mapping[Id[Port], tuple[Id[Conductor], ...]]
    layout: CoreLayout
    number: int


def _context(
    model: Model, layout: CoreLayout, problem: PlacementProblem, kit: SymbolKit, number: int
) -> _Ctx:
    ids = symbol_ids(model, kit)
    leads: dict[str, list[PickKey]] = defaultdict(list)
    for lead in kit:
        leads[ids[lead]].append(lead)
    pins: dict[str, list[tuple[Id[Port], str]]] = defaultdict(list)
    for port, ref in pin_names(model, kit, ids).items():
        pins[ref.sym].append((port, ref.pin))
    ends = build_indexes(model).conductors_by_port
    syms = {s.id: s for s in problem.symbols}
    return _Ctx(model, kit, syms, leads, pins, ends, layout, number)


def _functions(ctx: _Ctx, p: Placed) -> Iterable[_Spot]:
    """The function rows of a placed symbol: each lead and its pole-group members."""
    for lead in ctx.leads[p.sym]:
        for function in (function_of(ctx.model, lead), *ctx.kit[lead].members):
            yield _spot(ctx, "function", function, (p.page, (p.x, p.y)))


def _items(ctx: _Ctx, p: Placed) -> Iterable[_Spot]:
    """The item rows of a placed symbol: a connector box, a unit outline."""
    sym = ctx.syms[p.sym]
    for lead in ctx.leads[p.sym]:
        item = function_item(ctx.model, function_of(ctx.model, lead))
        if sym.box is not None:
            yield _spot(ctx, "item", item, (p.page, (p.x, p.y)), None, "box")
        if sym.boundary_of is not None:
            yield _spot(ctx, "item", item, (p.page, (p.x, p.y)), None, "outline")


def _pins(ctx: _Ctx, p: Placed) -> Iterable[_Spot]:
    """The port rows of a placed symbol, and the conductor-end row of each conductor at a port.

    A conductor end is a reference when a marker names its pin and no wire reaches it.
    """
    at = {q.pin: (q.x, q.y) for q in p.pin_xy}
    wired = {ref for ref, _ in ctx.layout.wired}
    marked = {m.end for m in ctx.layout.annotations.markers}
    for port, pin in ctx.pins[p.sym]:
        ref = PinRef(p.sym, pin)
        yield _spot(ctx, "port", port, (p.page, at[pin]), Shown.DRAWN)
        shown = Shown.REFERENCE if ref in marked and ref not in wired else Shown.DRAWN
        for conductor in ctx.ends.get(port, ()):
            yield _spot(ctx, "conductor", conductor, (p.page, at[pin]), shown, render_id(port))


def _markers(ctx: _Ctx) -> Iterable[_Spot]:
    """A reference port row for each port a marker's pin draws, at the marker's place."""
    named = {PinRef(sym, pin): port for sym, pins in ctx.pins.items() for port, pin in pins}
    for index, m in enumerate(ctx.layout.annotations.markers):
        if m.end in named:
            at = (m.x, m.y)
            yield _spot(ctx, "port", named[m.end], (m.page, at), Shown.REFERENCE, "ref", str(index))


def _spots(ctx: _Ctx) -> dict[tuple[str, ...], _Spot]:
    """Every spot by key; a function drawn by two pin views keeps its first."""
    found: dict[tuple[str, ...], _Spot] = {}
    placed = (p for page in ctx.layout.placement.pages for p in page.placed)
    for p in placed:
        for spot in (*_functions(ctx, p), *_pins(ctx, p), *_items(ctx, p)):
            found.setdefault(spot.key, spot)
    for spot in _markers(ctx):
        found.setdefault(spot.key, spot)
    return found


def memberships(  # noqa: PLR0913, PLR0917 - the stamp and set number join the layout, problem, kit and pages
    model: Model,
    layout: CoreLayout,
    problem: PlacementProblem,
    kit: SymbolKit,
    pages: Mapping[int, Page],
    stamp: str,
    number: int = 1,
) -> tuple[Membership, ...]:
    """One `Membership` per function, port, conductor end and item on each page of `layout`.

    The cell is `derive.frame_position.cell` of the place, the rank `reading_ranks` of the page.
    """
    spots = _spots(_context(model, layout, problem, kit, number))
    by_page: dict[int, dict[tuple[str, ...], tuple[int, int]]] = defaultdict(dict)
    for key, spot in spots.items():
        by_page[spot.page][key] = (spot.at[1], spot.at[0])
    ranks = {page: reading_ranks(points) for page, points in by_page.items()}
    return tuple(_row(model, pages[s.page], s, ranks[s.page][k], stamp) for k, s in spots.items())


def _row(model: Model, page: Page, spot: _Spot, rank: int, stamp: str) -> Membership:
    column, row = frame_cell(model, page, *spot.at)
    subject: dict[str, Any] = {"function": None, "port": None, "conductor": None, "item": None}
    subject[spot.field] = spot.subject
    return Membership(
        id=make_id(Membership, spot.key),
        key=spot.key,
        page=page.id,
        sheet=None,
        **subject,
        rank=rank,
        shown=spot.shown,
        cell=FrameCell(column=column, row=row),
        produced_by=stamp,
    )
