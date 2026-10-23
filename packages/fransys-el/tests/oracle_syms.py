"""The oracle of the symdef layer: the flat R0 values `placement_syms` built on the old engine.

A copy taken before the geometry moved into `fransys_layout.symbols`; it dies with the old
engine at SCHEMATIC-FLIP (SB9)."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from oracle_pins import box_of, geometry_of, nodes_of, pins_of

from fransys_layout.core import Box, Orientation, Pin, Size
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

if TYPE_CHECKING:
    from fransys_el.placement_env import Env
    from fransys_el.placement_kit import Pick, Rect

    from fransys_layout import SymbolGeometry
    from fransys_model.derive import Footprints
    from fransys_model.kernel import Id
    from fransys_model.vocab import Function

__all__ = ["Old", "old_of"]

TAG = "tag"
PLAIN: frozenset[Orientation] = frozenset({"R0", "R180"})
BOX: frozenset[Orientation] = frozenset({"R0"})


def _extent(box: Rect) -> Extent:
    """A geometry box as the `Extent` `derive.footprints` takes."""
    return Extent(x=box.x, y=box.y, width=box.width, height=box.height)


def _box(rect: Rect) -> Box:
    """A geometry box or a measured extent as a core `Box`."""
    return Box(rect.x, rect.y, rect.width, rect.height)


def _foot(env: Env, lead: Id[Function], geometry: SymbolGeometry) -> Footprints:
    """`derive.footprints` for the lead over its geometry."""
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
        place_text=c.place_text,
    )


def _label(env: Env, lead: Id[Function], geometry: SymbolGeometry) -> Size:
    """The size of the designation symbol: the tag slot widened to the measured tag text."""
    slot = next((s.box for s in geometry.slots if s.slot == TAG), None)
    if slot is None:
        return Size(0, 0)
    text = text_width(tag_text(env.model, lead), height=env.conventions.text_height)
    return Size(max(slot.width, text), slot.height)


def _table(foot: Footprints) -> Size | None:
    """The contact table's size when the footprint holds one (a coil with contacts), else None."""
    room = foot.standalone.height - foot.alone.height
    return Size(foot.standalone.width, room) if room > 0 else None


def _boundary(env: Env, lead: Id[Function]) -> str | None:
    """The unit whose boundary `lead` is: its item's own unit first, else the lowest id."""
    own = item_unit(env.model, function_item(env.model, lead))
    held = [u for u in unit_ids(env.model) if lead in boundary(env.model, u)]
    if not held:
        return None
    return (own if own in held else held[0]).value


@dataclass(frozen=True, slots=True)
class Old:
    """What the old builder gave one symbol, as flat R0 values."""

    label: Size
    body: Box
    keepout: Box
    footprint: Box
    pins: tuple[Pin, ...]
    nodes: tuple[tuple[str, ...], ...]
    orientations: frozenset[Orientation]
    box: object
    row_footprint: Box | None
    table: Size | None


def old_of(env: Env, lead: Id[Function], pick: Pick) -> Old:
    """The old builder's values for `lead` drawn as `pick`."""
    geometry = geometry_of(env, lead, pick)
    pins = pins_of(env, pick, geometry)
    box = box_of(env, pick, geometry, pins)
    strip = strip_of(env.model, function_item(env.model, lead))
    foot = _foot(env, lead, geometry)
    return Old(
        _label(env, lead, geometry),
        _box(geometry.body),
        _box(geometry.keepout),
        _box(foot.standalone),
        pins,
        nodes_of(geometry),
        BOX if box else PLAIN,
        box,
        None if strip is None else _box(foot.in_strip_row),
        _table(foot),
    )
