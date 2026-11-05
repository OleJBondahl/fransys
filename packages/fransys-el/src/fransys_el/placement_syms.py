"""One `Sym` per picked function: geometry, footprint, sizes and the facts it is read by."""

from typing import TYPE_CHECKING

from fransys_layout.core import Box, Orientation, Sym
from fransys_layout.symbols import Ask, TableAsk, library_symbol, symbol_views
from fransys_model.derive import (
    coil_cells,
    function_item,
    item_unit,
    strip_of,
    tag_text,
)
from fransys_model.derive.contact_rows import table_geometry

from .footprints import footprints
from .kit_keys import PickKey, function_of, tag_of
from .placement_groups import group_of
from .placement_pins import box_of, nodes_of, pins_of, shape_of, symbol_of
from .placement_where import where_room
from .write_markings import marking_slots

if TYPE_CHECKING:
    from electrical_symbols import Library
    from fransys_layout.symbols import Shape
    from fransys_model.derive import Footprints
    from fransys_model.kernel import Id
    from fransys_model.vocab import Function

    from .placement_env import Env
    from .placement_kit import Pick

__all__ = ["syms_of"]

PLAIN: tuple[Orientation, ...] = ("R0", "R180")
BOX: tuple[Orientation, ...] = ("R0",)


def _foot(env: Env, lead: Id[Function], shape: Shape) -> Footprints:
    """`footprints` for the lead over its shape, with the texts the model prints for it."""
    c = env.conventions
    no, nc = coil_cells(env.model, lead)
    rows = max(len(no), len(nc))
    return footprints(
        env.library,
        body=shape.body,
        slots=dict(shape.slots),
        tag=tag_text(env.model, lead),
        tag_side=c.tag_side,
        text_height=c.text_height,
        cells=(no, nc),
        table_height=table_geometry(rows, c.step, c.pad, headed=False).height,
        step=c.step,
        pad=c.pad,
    )


def _table(foot: Footprints, library: Library) -> TableAsk | None:
    """The coil's one contact table: its cells, measured with its top-left at the origin."""
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
        library_symbol(library, "contact-head"),
        texts,
        (0, 0),
    )


def sym_and_table(env: Env, lead: PickKey, pick: Pick) -> tuple[Sym, Box | None]:
    """The `Sym` of `lead` drawn as `pick`, and its contact table's keep-out (top-left at 0, 0)."""
    symbol = symbol_of(env, lead, pick)
    shape = shape_of(env, lead, pick, symbol)
    pins = pins_of(env, pick, shape)
    box = box_of(pick, shape, pins)
    function = function_of(env.model, lead)
    item = function_item(env.model, function)
    strip = strip_of(env.model, item)
    table = _table(_foot(env, function, shape), env.library)
    ask = Ask(
        BOX if box else PLAIN,
        [p.id for p in pins],
        "tag",
        tag_of(env.model, lead) + where_room(env, function),
        env.conventions.text_height,
        table,
        strip is not None,
        marking_slots(env.model, pick, env.library),
    )
    drawn = symbol_views(symbol, env.library, ask)
    sym = Sym(
        id=env.ids[lead],
        group=group_of(env.model, function),
        unit="" if (unit := item_unit(env.model, item)) is None else unit.value,  # empty for the integrating script's own wiring
        label=drawn.label,
        pins=pins,
        nodes=nodes_of(shape),
        views=drawn.views,
        box=box,
        row_group=None if strip is None else strip.value,
        item=item.value,
        child_of=env.parents[item].value if item in env.parents else None,
        rank=env.ranks[lead],
    )
    return sym, drawn.table


def syms_of(env: Env, tables: dict[str, Box] | None = None) -> tuple[Sym, ...]:
    """Every `Sym` in function order (`symbol_ids`); `tables` gets the table box of each coil with one."""
    found = [sym_and_table(env, lead, env.kit[lead]) for lead in env.ids]  # env.ids stands in function order (model-0396)
    if tables is not None:
        tables.update({s.id: t for s, t in found if t is not None})
    return tuple(s for s, _ in found)
