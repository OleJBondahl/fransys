"""One `Sym` per picked function: geometry, footprint, sizes and the facts it is read by."""

from typing import TYPE_CHECKING

from fransys_layout.core import Box, Orientation, Sym
from fransys_layout.symbols import Ask, TableAsk, library_symbol, symbol_views
from fransys_model.derive import (
    Extent,
    boundary,
    footprints,
    function_item,
    item_unit,
    strip_of,
    unit_ids,
)
from fransys_model.derive.drawing_text import coil_heading

from .kit_keys import PickKey, function_of, tag_of
from .placement_groups import group_of
from .placement_pins import box_of, nodes_of, pins_of, shape_of, symbol_of

if TYPE_CHECKING:
    from electrical_symbols import Library
    from fransys_layout.symbols import Shape
    from fransys_model.derive import Footprints
    from fransys_model.kernel import Id
    from fransys_model.vocab import Function, Item

    from .placement_env import Env
    from .placement_kit import Pick

__all__ = ["heading_of", "syms_of"]

PLAIN: tuple[Orientation, ...] = ("R0", "R180")
BOX: tuple[Orientation, ...] = ("R0",)


def _extent(box: Box) -> Extent:
    """A layer box as the `Extent` `derive.footprints` takes."""
    return Extent(x=box.x, y=box.y, width=box.w, height=box.h)


def _foot(env: Env, lead: Id[Function], shape: Shape) -> Footprints:
    """`derive.footprints` for the lead over its shape."""
    c = env.conventions
    return footprints(
        env.model,
        lead,
        body=_extent(shape.body),
        slots={name: _extent(box) for name, box in shape.slots.items()},
        tag_side=c.tag_side,
        text_height=c.text_height,
        step=c.step,
        pad=c.pad,
        place_text=c.place_text,
    )


def _table(foot: Footprints, library: Library, heading: str | None = None) -> TableAsk | None:
    """The coil's one contact table: its cells, measured with its top-left at the origin.

    A `heading` (from `heading_of`) takes the headed head; none keeps the lone table's head.
    """
    if not (foot.no_cells or foot.nc_cells):
        return None
    texts = [
        {
            **({"no": foot.no_cells[k]} if k < len(foot.no_cells) else {}),
            **({"nc": foot.nc_cells[k]} if k < len(foot.nc_cells) else {}),
        }
        for k in range(max(len(foot.no_cells), len(foot.nc_cells)))
    ]
    return TableAsk(
        library_symbol(library, "contact-row"),
        library_symbol(library, "contact-head" if heading is None else "contact-head-headed"),
        texts,
        (0, 0),
        heading,
    )


def heading_of(env: Env, lead: Id[Function]) -> str:
    """The designation a shared foot prints over `lead`'s table: the coil's tag in its own unit."""
    item = function_item(env.model, lead)
    return coil_heading(env.model, item, unit=item_unit(env.model, item))


def _boundary(env: Env, lead: Id[Function]) -> str | None:
    """The unit whose boundary `lead` is: its item's own unit first, else the lowest id."""
    own = item_unit(env.model, function_item(env.model, lead))
    held = [u for u in unit_ids(env.model) if lead in boundary(env.model, u)]
    if not held:
        return None
    return (own if own in held else held[0]).value


def sym_and_table(env: Env, lead: PickKey, pick: Pick) -> tuple[Sym, Box | None]:
    """The `Sym` of `lead` drawn as `pick`, and its contact table's keep-out (top-left at 0, 0)."""
    symbol = symbol_of(env, lead, pick)
    shape = shape_of(env, lead, pick, symbol)
    pins = pins_of(env, pick, shape)
    box = box_of(env, pick, shape, pins)
    function = function_of(env.model, lead)
    item = function_item(env.model, function)
    strip = strip_of(env.model, item)
    table = _table(_foot(env, function, shape), env.library)
    ask = Ask(
        BOX if box else PLAIN,
        [p.id for p in pins],
        "tag",
        tag_of(env.model, lead),
        env.conventions.text_height,
        table,
        strip is not None,
    )
    drawn = symbol_views(symbol, env.library, ask)
    sym = Sym(
        id=env.ids[lead],
        group=group_of(env.model, function),
        unit=_unit(env, item),
        label=drawn.label,
        pins=pins,
        nodes=nodes_of(shape),
        views=drawn.views,
        box=box,
        row_group=None if strip is None else strip.value,
        item=item.value,
        child_of=env.parents[item].value if item in env.parents else None,
        boundary_of=_boundary(env, function),
    )
    return sym, drawn.table


def _unit(env: Env, item: Id[Item]) -> str:
    """The unit id text of `item`, empty for the integrating script's own wiring."""
    unit = item_unit(env.model, item)
    return "" if unit is None else unit.value


def syms_of(env: Env, tables: dict[str, Box] | None = None) -> tuple[Sym, ...]:
    """Every `Sym` in the kit's order; `tables` gets the table box of each coil with one."""
    found = [sym_and_table(env, lead, pick) for lead, pick in env.kit.items()]
    if tables is not None:
        tables.update({s.id: t for s, t in found if t is not None})
    return tuple(s for s, _ in found)
