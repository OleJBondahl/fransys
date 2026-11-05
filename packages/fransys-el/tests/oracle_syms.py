"""The oracle of the symdef layer: the flat R0 values `placement_syms` built on the old engine.

A copy taken before the geometry moved into `fransys_layout.symbols`; it dies with the old
engine at SCHEMATIC-FLIP (SB9)."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fransys_el.footprints import footprints
from oracle_pins import box_of, geometry_of, nodes_of, pins_of

from fransys_layout.core import Box, Orientation, Pin, Size
from fransys_layout.symbols import text_width_g
from fransys_model.derive import (
    coil_cells,
    function_item,
    strip_of,
    tag_text,
)
from fransys_model.derive.contact_rows import table_geometry

if TYPE_CHECKING:
    from fransys_el.placement_env import Env
    from fransys_el.placement_kit import Pick

    from fransys_layout import SymbolGeometry
    from fransys_model.derive import Footprints
    from fransys_model.kernel import Id
    from fransys_model.vocab import Function

__all__ = ["Old", "old_of"]

TAG = "tag"
PLAIN: frozenset[Orientation] = frozenset({"R0", "R180"})
BOX: frozenset[Orientation] = frozenset({"R0"})


def _box(rect: Any) -> Box:
    """A geometry box or a measured extent as a core `Box`."""
    return Box(rect.x, rect.y, rect.width, rect.height)


def _foot(env: Env, lead: Id[Function], geometry: SymbolGeometry) -> Footprints:
    """`footprints` for the lead over its geometry."""
    c = env.conventions
    no, nc = coil_cells(env.model, lead)
    return footprints(
        env.library,
        body=_box(geometry.body),
        slots={s.slot: _box(s.box) for s in geometry.slots},
        tag=tag_text(env.model, lead),
        tag_side=c.tag_side,
        text_height=c.text_height,
        cells=(no, nc),
        table_height=table_geometry(max(len(no), len(nc)), c.step, c.pad, headed=False).height,
        step=c.step,
        pad=c.pad,
    )


def _label(env: Env, lead: Id[Function], geometry: SymbolGeometry) -> Size:
    """The size of the designation symbol: the tag slot widened to the measured tag text."""
    slot = next((s.box for s in geometry.slots if s.slot == TAG), None)
    if slot is None:
        return Size(0, 0)
    text = text_width_g(env.library.font, tag_text(env.model, lead), height=env.conventions.text_height)
    return Size(max(slot.width, text), slot.height)


def _table(foot: Footprints) -> Size | None:
    """The contact table's size when the footprint holds one (a coil with contacts), else None."""
    room = foot.standalone.height - foot.alone.height
    return Size(foot.standalone.width, room) if room > 0 else None


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
    box = box_of(pick, geometry, pins)
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
