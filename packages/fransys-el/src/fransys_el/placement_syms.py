"""One `Sym` per picked function: geometry, footprint, sizes and the facts it is read by."""

from typing import TYPE_CHECKING

from fransys_layout.core import Box, Orientation, Size, Sym, natural_key
from fransys_model.derive import (
    Extent,
    boundary,
    footprints,
    function_item,
    item_unit,
    strip_of,
    tag_text,
    unit_ids,
)
from fransys_model.derive.text_width import text_width

from .placement_groups import group_of
from .placement_pins import box_of, geometry_of, nodes_of, pins_of

if TYPE_CHECKING:
    from fransys_layout import SymbolGeometry
    from fransys_model.derive import Footprints
    from fransys_model.kernel import Id
    from fransys_model.vocab import Function, Item

    from .placement_env import Env
    from .placement_kit import Pick, Rect

__all__ = ["syms_of"]

TAG = "tag"
PLAIN: frozenset[Orientation] = frozenset({"R0", "R180"})
BOX: frozenset[Orientation] = frozenset({"R0"})


def _extent(box: Rect) -> Extent:
    """A geometry box as the `Extent` `derive.footprints` takes."""
    return Extent(x=box.x, y=box.y, width=box.width, height=box.height)


def _box(rect: Rect) -> Box:
    """A geometry box or a measured extent as a core `Box`."""
    return Box(rect.x, rect.y, rect.width, rect.height)


def _foot(env: Env, lead: Id[Function], geometry: SymbolGeometry, tiers: int) -> Footprints:
    """`derive.footprints` for the lead over its geometry, `tiers` tables high."""
    c = env.conventions
    return footprints(
        env.model,
        lead,
        body=_extent(geometry.body),
        slots={s.slot: _extent(s.box) for s in geometry.slots},
        tag_side=c.tag_side,
        text_height=c.text_height,
        step=c.step,
        pad=c.pad,
        tiers=tiers,
        place_text=c.place_text,
    )


def _label(env: Env, lead: Id[Function], geometry: SymbolGeometry) -> Size:
    """The size of the designation symbol: the tag slot widened to the measured tag text."""
    slot = next((s.box for s in geometry.slots if s.slot == TAG), None)
    if slot is None:
        return Size(0, 0)
    text = text_width(tag_text(env.model, lead), height=env.conventions.text_height)
    return Size(max(slot.width, text), slot.height)


def _table(env: Env, lead: Id[Function], geometry: SymbolGeometry, foot: Footprints) -> Size | None:
    """The contact table's size when the footprint holds one (a coil with contacts), else None."""
    bare = _foot(env, lead, geometry, 0).standalone
    room = foot.standalone.height - bare.height
    return Size(foot.standalone.width, room) if room > 0 else None


def _boundary(env: Env, lead: Id[Function]) -> str | None:
    """The unit whose boundary `lead` is: its item's own unit first, else the lowest id."""
    own = item_unit(env.model, function_item(env.model, lead))
    held = [u for u in unit_ids(env.model) if lead in boundary(env.model, u)]
    if not held:
        return None
    return (own if own in held else held[0]).value


def sym_of(env: Env, lead: Id[Function], pick: Pick) -> Sym:
    """The `Sym` of `lead` drawn as `pick`."""
    geometry = geometry_of(env, lead, pick)
    pins = pins_of(env, pick, geometry)
    box = box_of(env, pick, geometry, pins)
    item = function_item(env.model, lead)
    strip = strip_of(env.model, item)
    foot = _foot(env, lead, geometry, env.conventions.tiers)
    return Sym(
        id=env.ids[lead],
        group=group_of(env.model, lead),
        unit=_unit(env, item),
        label=_label(env, lead, geometry),
        body=_box(geometry.body),
        keepout=_box(geometry.keepout),
        footprint=_box(foot.standalone),
        pins=pins,
        nodes=nodes_of(geometry),
        orientations=BOX if box else PLAIN,
        box=box,
        row_footprint=None if strip is None else _box(foot.in_strip_row),
        row_group=None if strip is None else strip.value,
        item=item.value,
        child_of=env.parents[item].value if item in env.parents else None,
        table=_table(env, lead, geometry, foot),
        boundary_of=_boundary(env, lead),
    )


def _unit(env: Env, item: Id[Item]) -> str:
    """The unit id text of `item`, empty for the integrating script's own wiring."""
    unit = item_unit(env.model, item)
    return "" if unit is None else unit.value


def syms_of(env: Env) -> tuple[Sym, ...]:
    """Every `Sym`, in natural order of id."""
    found = [sym_of(env, lead, pick) for lead, pick in env.kit.items()]
    return tuple(sorted(found, key=lambda s: natural_key(s.id)))
