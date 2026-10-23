"""The `layout.link_marker` records of a core layout's markers (CORE-TEXTS C, Ruling 69).

Each reference end the core placed is one record; the derive marker functions print its text.
Two ends are a plain pair; more are a star: the first end the hub (`REF`), the rest its `BRANCH`es.
A lone end (a stub or a copy) is an off stub, written by `write_stubs`.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from electrical_symbols import MARKER_FACING
from fransys_model.kernel import make_id
from fransys_model.layout import LinkMarker, MarkerSide, Side, StarKind

from .placement_ids import pin_names, symbol_ids
from .placement_kit import refuse
from .placement_markers import ARROW, LONE, marker_fit, pin_ports
from .placement_views import marker_boxes
from .placement_widest import link_fit
from .write_stubs import far_port, off_stub

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from electrical_symbols import Library
    from fransys_layout.core import Box, CoreLayout, Marker, Orientation, PinRef
    from fransys_model.kernel import Id, Model
    from fransys_model.layout import Page
    from fransys_model.vocab import Port, Unit

    from .placement_kit import SymbolKit

__all__ = ["link_markers"]

_KEY = ("layout", "core", "link_marker")
_TAG = "tag"  # a tag prints a reference line, so its record holds the wide box
_FACES = {turn: Side[side] for side, turn in MARKER_FACING.items()}


def marker_key(kind: str, marker: Marker, index: int, number: int) -> tuple[str, ...]:
    """The key of `marker`, the `index`th of its reference in drawing set `number`.

    Page numbers restart in every set, so the set's number is in the key (as a drawn wire's is);
    the kind is the key's fourth part.
    """
    return (*_KEY, kind, str(number), marker.net, str(marker.page), str(index))


def _groups(markers: Sequence[Marker]) -> dict[tuple[str, str], list[Marker]]:
    found: dict[tuple[str, str], list[Marker]] = defaultdict(list)
    for marker in markers:
        found[marker.net, str(marker.kind)].append(marker)  # the one read of a marker's kind
    return found


def _star(count: int, index: int) -> StarKind | None:
    """A pair has no star; of more ends the first is the `REF` hub and the rest its `BRANCH`es."""
    if count == 2:  # noqa: PLR2004 - two ends are a plain pair
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
    fit: Mapping[tuple[PinRef, str], Mapping[Orientation, Box]]
    link: Mapping[Orientation, Box]
    stamp: str


def _record(
    ctx: _Ctx, group: Sequence[Marker], kind: str, index: int, ids: Sequence[Id[LinkMarker]]
) -> LinkMarker:
    """The record of `group[index]`: an off stub for a one-end kind, else a pair or star end."""
    marker, key = group[index], marker_key(kind, group[index], index, ctx.number)
    views = ctx.link if kind in (ARROW, _TAG) else ctx.fit.get((marker.end, kind)) or ctx.boxes
    box, page, port = views[marker.orient], ctx.pages[marker.page], ctx.ports[marker.end]
    facing = _FACES[marker.orient]
    if kind in LONE:
        at = (marker.x, marker.y, box.w, box.h)
        ends = far_port(ctx.model, ctx.pin_ports[marker.end])
        return off_stub(key, page, ends, at, facing, stamp=ctx.stamp)
    return LinkMarker(
        id=ids[index],
        key=key,
        page=page.id,
        port=port,
        side=MarkerSide.OWNER if index == 0 else MarkerSide.USER,
        partner=ids[1 if index == 0 else 0],
        x=marker.x,
        y=marker.y,
        width=box.w,
        height=box.h,
        produced_by=ctx.stamp,
        star=_star(len(group), index),
        facing=facing,
    )


def link_markers(  # noqa: PLR0913 - the stamp and library join the layout, model, kit and pages
    layout: CoreLayout,
    model: Model,
    kit: SymbolKit,
    pages: Mapping[int, Page],
    *,
    stamp: str,
    library: Library,
    number: int,
    unit: Id[Unit] | None,
) -> tuple[LinkMarker, ...]:
    """One `LinkMarker` per marker: a pair or star end, or a lone off stub; a bad pin is refused.

    A stub or a copy has one end, so each is its own off stub whose far end is read from the
    conductor at its port (`write_stubs.far_port`). `number` is the drawing set's.
    """
    boxes = marker_boxes(library)
    fit = marker_fit(model, kit, unit, library, (m.end for m in layout.annotations.markers))
    link = link_fit(model, kit, library, unit)
    ctx = _Ctx(
        model, _ports(model, kit), pin_ports(model, kit), pages, number, boxes, fit, link, stamp
    )
    found = []
    for (net, kind), group in _groups(layout.annotations.markers).items():
        for marker in group:
            if marker.end not in ctx.ports or marker.page not in pages:
                refuse(
                    f"marker of {net} on page {marker.page}",
                    f"its pin {marker.end} or page is not in the written layout: pass the kit",
                )
        ids = [make_id(LinkMarker, marker_key(kind, m, i, number)) for i, m in enumerate(group)]
        found.extend(_record(ctx, group, kind, i, ids) for i in range(len(group)))
    return tuple(found)
