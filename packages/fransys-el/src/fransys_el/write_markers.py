"""The `layout.link_marker` records of a core layout's markers (CORE-TEXTS C, Ruling 69).

Each reference end the core placed is one record; the derive marker functions print its text.
Two ends are a plain pair; more are a star: the first end the hub (`REF`), the rest its `BRANCH`es.
A lone end (a stub or a copy) is an off stub, written by `write_stubs`.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from electrical_symbols import MARKER_FACING
from fransys_layout.core import stub_views
from fransys_model.kernel import make_id
from fransys_model.layout import LinkMarker, MarkerPair, MarkerSide, Side, StarKind

from .placement_ids import pin_names, symbol_ids
from .placement_kit import refuse
from .placement_markers import ARROW, LONE, pin_ports, stub_fit
from .placement_views import marker_boxes
from .placement_widest import link_fit
from .write_pages import STAMP
from .write_stubs import drawn_ports, far_port, stub_ends

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.core import Box, Marker, Orientation, PinRef
    from fransys_model.kernel import Id, Model
    from fransys_model.layout import Page
    from fransys_model.vocab import Item, Port

    from .placement_kit import SymbolKit
    from .placement_markers import Fit, StubLines, StubTable
    from .write_pages import Written

__all__ = ["link_markers", "marker_ids"]

_PAIR = 2  # two ends are a plain pair
_KEY = ("layout", "core", "link_marker")
_TAG = "tag"  # a tag prints a reference line, so its record holds the wide box
_FACES = {turn: Side[side] for side, turn in MARKER_FACING.items()}


def _groups(markers: Sequence[Marker]) -> dict[tuple[str, int, str], list[int]]:
    """The positions of each Ref's markers (net, the cut that planned it, kind): one pair or star (R550)."""
    found: dict[tuple[str, int, str], list[int]] = defaultdict(list)
    for position, marker in enumerate(markers):
        found[marker.net, marker.ref, str(marker.kind)].append(position)  # the one read of a kind
    return found


def marker_keys(markers: Sequence[Marker], number: int) -> tuple[tuple[str, ...], ...]:
    """The key of each marker in drawing set `number`, in the markers' order: the one marker identity.

    Page numbers restart in every set, so the set's number is in the key (as a drawn wire's is). A fan's
    Refs count their earlier ends, so the keys of one net and kind differ. `LinkMarker` and `Membership` take it from here.
    """
    keys: list[tuple[str, ...]] = [()] * len(markers)
    before: dict[tuple[str, str], int] = defaultdict(int)
    for (net, _, kind), positions in _groups(markers).items():
        for i, position in enumerate(positions):
            keys[position] = (*_KEY, kind, str(number), net, str(markers[position].page), str(before[net, kind] + i))
        before[net, kind] += len(positions)
    return tuple(keys)


def marker_ids(markers: Sequence[Marker], number: int) -> tuple[Id[LinkMarker], ...]:
    """The `LinkMarker` id of each marker, in the markers' order."""
    return tuple(make_id(LinkMarker, key) for key in marker_keys(markers, number))


def _star(count: int, index: int) -> StarKind | None:
    """A pair has no star; of more ends the first is the `REF` hub and the rest its `BRANCH`es."""
    if count == _PAIR:
        return None
    return StarKind.REF if index == 0 else StarKind.BRANCH


def _ports(model: Model, kit: SymbolKit) -> dict[object, Id[Port]]:
    """The model port that each symbol pin draws, the lowest where several do."""
    found: dict[object, Id[Port]] = {}
    for port, pin in pin_names(model, kit, symbol_ids(model, kit)).items():
        if pin not in found or port < found[pin]:
            found[pin] = port
    return found


@dataclass(frozen=True)
class _Ctx:
    """What a marker record reads: the model, the pin ports, the pages, the box sizes, the stamp."""

    model: Model
    ports: Mapping[object, Id[Port]]
    pin_ports: Mapping[PinRef, Sequence[Id[Port]]]
    pages: Mapping[int, Page]
    number: int
    boxes: Mapping[Orientation, Box]
    fit: tuple[Fit, StubLines, StubTable]
    link: Mapping[Orientation, Box]
    drawn: frozenset[tuple[Id[Port], Id[Port]]]


def _ends(ctx: _Ctx, marker: Marker) -> tuple[tuple[Id[Port], Id[Port], Id[Item] | None], ...]:
    """The `(port, far, carrier)` of every conductor the marker ends: each far pin in `marker.far`, read at its pin or one it also stands for."""
    near = [ctx.pin_ports.get(pin, ()) for pin in (marker.end, *marker.also)]
    if not marker.far:
        return (far_port(ctx.model, near[0]),)
    found: list[tuple[Id[Port], Id[Port], Id[Item] | None]] = []
    for far in marker.far:
        ends = next((e for ports in near if (e := stub_ends(ctx.model, ports, ctx.pin_ports.get(far, ())))), ())
        if not ends:
            refuse(f"stub at {marker.end}", f"no conductor to {far} leaves it, so its far end is unknown")
        found += [end for end in ends if end not in found]
    return tuple(found)


def _stub_views(fit: tuple[Fit, StubLines, StubTable], marker: Marker) -> Mapping[Orientation, Box] | None:
    """The boxes the core sized the marker with: its ledger end's lines first (`stub_views`, R1597)."""
    return stub_views(fit[1], fit[2], marker.end, marker.also, marker.far)


def _record(
    ctx: _Ctx,
    group: Sequence[Marker],
    kind: str,
    index: int,
    keys: Sequence[tuple[str, ...]],
) -> LinkMarker:
    """The record of `group[index]`: an off stub for a one-end kind, else a pair or star end."""
    marker, key = group[index], keys[index]
    ids = [make_id(LinkMarker, k) for k in keys]
    views = ctx.link if kind in (ARROW, _TAG) else _stub_views(ctx.fit, marker) or ctx.fit[0].get((marker.end, kind)) or ctx.boxes
    box, page, port = views[marker.orient], ctx.pages[marker.page], ctx.ports[marker.end]
    facing = _FACES[marker.orient]
    lone = kind in LONE
    ends = _ends(ctx, marker) if lone else ((port, port, None),)  # `far` is read only for a lone stub (pairs)
    return LinkMarker(
        id=ids[index],
        key=key,
        page=page.id,
        port=ends[0][0],
        side=MarkerSide.OWNER if lone or index == 0 else MarkerSide.USER,
        partner=ids[index] if lone else ids[1 if index == 0 else 0],
        x=marker.x,
        y=marker.y,
        width=box.w,
        height=box.h,
        produced_by=STAMP,
        star=StarKind.OFF if lone else _star(len(group), index),
        pairs=tuple(MarkerPair(port=a, far=b, carrier=c) for a, b, c in ends) if lone else (),
        facing=facing,
    )


def _refuse_unwritten(ctx: _Ctx, net: str, group: list[Marker]) -> None:
    """Refuse a marker whose pin or page the written layout does not hold."""
    for marker in group:
        if marker.end not in ctx.ports or marker.page not in ctx.pages:
            refuse(f"marker of {net} on page {marker.page}", f"its pin {marker.end} or page is not in the written layout: pass the kit")


def link_markers(w: Written) -> tuple[LinkMarker, ...]:
    """One `LinkMarker` per marker: a pair or star end, or a lone off stub; a bad pin is refused.

    A stub or a copy has one end, so each is its own off stub whose far end is read from the
    conductor at its port (`write_stubs.far_port`).
    """
    model, kit, pages, library, unit = w.model, w.kit, w.pages, w.library, w.within
    markers = w.layout.annotations.markers
    boxes = marker_boxes(library)
    pins = pin_ports(model, kit)
    drawn = drawn_ports(pins, w.layout.drawn)
    fit, lines, table = stub_fit(model, kit, (unit, library), {p for m in markers for p in (m.end, *m.also)}, [[m.end, *m.also] for m in markers])
    link = link_fit(model, kit, library, unit)
    ctx = _Ctx(model, _ports(model, kit), pins, pages, w.owner.number, boxes, (fit, lines, table), link, drawn)
    keys = marker_keys(markers, w.owner.number)
    found = []
    for (net, _, kind), positions in _groups(markers).items():
        group = [markers[p] for p in positions]
        _refuse_unwritten(ctx, net, group)
        group_keys = [keys[p] for p in positions]
        found.extend(_record(ctx, group, kind, i, group_keys) for i in range(len(group)))
    return tuple(found)
