"""The hangings of one page: a box at each pin end the page draws, built once (layout-0395)."""

from __future__ import annotations

from functools import reduce
from typing import TYPE_CHECKING

from .anchors import folded
from .band import arrow_box
from .geometry import shift, union
from .hang_levels import extra
from .hangings import Hanging
from .ref_kind import kind_of
from .route_env import pin_sides
from .sides import step_out
from .values import Box, RefKind, StandClass

if TYPE_CHECKING:
    from collections.abc import Container, Iterable, Mapping

    from .flow_values import Block
    from .pack import PlacedColumn
    from .sym_values import Sym
    from .values import Anchor, Options, Orientation, PagePlan, PinRef, PlacementProblem, Ref, Side

    Key = tuple[str, str, Orientation]


def page_owners(plan: PagePlan, pcs: Mapping[str, PlacedColumn], blocks: Mapping[str, Block]) -> frozenset[str]:
    """The symbols the page holds: the cells of its columns and the anchors of its cards."""
    cells = {c.sym for pc in pcs.values() for lane in pc.lanes for c in lane}
    cards = {b.anchor for row in plan.rows for n in row.blocks if (b := blocks[n]).anchor}
    return frozenset(cells | cards)


def _marker_rel(options: Options, side: Side, pin: PinRef, kind: str) -> Box | None:
    """The marker's drawn box from its pin, as `text_ends.pin_stand` stands it.

    None where no marker size was passed (neither `marker` nor a fit for this end): nothing to keep.
    """
    if options.marker is None and (pin, kind) not in options.marker_fit:
        return None
    box = arrow_box(options, side, 0, 0, (pin, kind))
    # a stub marker stands `open_stub` out along the side, past the open end's stub
    return shift(box, *step_out(side, 0, 0, options.open_stub if kind == RefKind.STUB else 0))


def _ends(refs: Iterable[Ref], page: int) -> Iterable[tuple[PinRef, str]]:
    """(pin, kind) of each drawn PIN-class end of the page, not an arrow's (a trunk end and a leg hang at their trunk, CL3)."""
    for ref in refs:
        if (kind := kind_of(ref)) is not RefKind.ARROW:
            for end in ref.ends:
                if end.pin is not None and end.page == page and end.stand is StandClass.PIN:
                    yield end.pin, str(kind)


def _anchor_rel(anchor: Anchor, side: Side) -> Box | None:
    """The deepest outline of the anchor's poses for `side`, from its pin (as `anchors._anchored` folds it)."""
    boxes = [pose.outline for s, pose in anchor.poses if s == side]
    return reduce(union, boxes) if boxes else None


def page_hangings(
    refs: Iterable[Ref],
    problem: PlacementProblem,
    options: Options,
    page_owners: tuple[int, frozenset[str]],
    stands: Mapping[PinRef, Mapping[Orientation, PinRef | None]] | None = None,
) -> Mapping[Key, tuple[Hanging, ...]]:
    """Per (symbol, pin, orientation), one Hanging per drawn thing at that pin.

    The plan's ends come first, in plan order, then the anchors of the page's symbols (`owners`, with the page number in `page_owners`).
    A mixed pin's marker hangs at the pin `stands` names for the orientation: `Hanging.pin` is the pin it stands at.
    """
    page, owners = page_owners
    sides = pin_sides(problem)
    by_pin: dict[tuple[str, str], list[tuple[Orientation, Side]]] = {}
    for (sym, pin, orient), side in sides.items():
        by_pin.setdefault((sym, pin), []).append((orient, side))
    out: dict[Key, list[Hanging]] = {}
    for end, kind in _ends(refs, page):
        for orient, _ in by_pin.get((end.sym, end.pin), ()):
            pin = (stands or {}).get(end, {}).get(orient) or end
            at = sides[pin.sym, pin.pin, orient]
            if (rel := _marker_rel(options, at, end, kind)) is not None:
                out.setdefault((pin.sym, pin.pin, orient), []).append(Hanging(pin, at, rel, kind))
    for anchor in (a for a in problem.anchors if a.pin.sym in owners):
        for orient, side in by_pin.get((anchor.pin.sym, anchor.pin.pin), ()):
            if (rel := _anchor_rel(anchor, side)) is not None:
                hanging = Hanging(anchor.pin, side, rel, "anchor")
                out.setdefault((anchor.pin.sym, anchor.pin.pin, orient), []).append(hanging)
    return {key: tuple(hs) for key, hs in out.items()}


def _led(h: Hanging, leads: Container[PinRef], options: Options) -> Hanging:
    if h.kind == "anchor" or h.pin not in leads:
        return h
    by = step_out(h.side, 0, 0, options.wiring_grid)
    return h._replace(box_rel=shift(h.box_rel, *by))


def led(hangings: Mapping[Key, tuple[Hanging, ...]], leads: Container[PinRef], options: Options) -> Mapping[Key, tuple[Hanging, ...]]:
    """`hangings` with the markers at a lead pin a wiring grid further out, and a "lead" hanging from the pin over the lead and its markers."""
    out: dict[Key, tuple[Hanging, ...]] = {}
    for key, hs in hangings.items():
        shifted = tuple(_led(h, leads, options) for h in hs)
        spans: dict[tuple[PinRef, Side], Box] = {}
        for h in (h for h in shifted if h.kind != "anchor" and h.pin in leads):
            spans[h.pin, h.side] = union(spans.get((h.pin, h.side)) or _lead_box(h.side, options), h.box_rel)
        out[key] = (*shifted, *(Hanging(pin, side, box, "lead") for (pin, side), box in spans.items()))
    return out


def _lead_box(side: Side, options: Options) -> Box:
    """The box of a lead wire from a pin on `side`: one wiring grid out, no width."""
    x, y = step_out(side, 0, 0, options.wiring_grid)
    return Box(min(0, x), min(0, y), abs(x), abs(y))


def stack_extra(sym: Sym, options: Options) -> int:
    """The G the fitted flags at the pins of `sym` stack beyond one level, the deepest view's (the cut's bound)."""
    fits = [k for k in options.marker_fit if k[0].sym == sym.id]
    best = 0
    for view in sym.views.values():
        items = []
        for pin, kind in fits:
            idx = next(i for i, p in enumerate(sym.pins) if p.id == pin.pin)
            turn = view.pins[idx]
            if (rel := _marker_rel(options, turn.side, pin, kind)) is not None:
                items.append((turn.dx, Hanging(pin, turn.side, rel, kind)))
        best = max(best, extra(items))
    return best


def fold_page(
    plain: Mapping[str, Sym],
    refs: Iterable[Ref],
    problem: PlacementProblem,
    page: tuple[int, frozenset[str]] | tuple[int, frozenset[str], Mapping[PinRef, Mapping[Orientation, PinRef | None]]],
    leads: tuple[Container[PinRef], Options],
) -> tuple[Mapping[Key, tuple[Hanging, ...]], dict[str, Sym]]:
    """The page's hangings and the symbols that hold them: the one fold chain, read by the cut and the placement."""
    options = leads[1]
    hangings = led(page_hangings(refs, problem, options, page[:2], *page[2:]), leads[0], options)
    return hangings, folded(plain, hangings, problem.anchors)
