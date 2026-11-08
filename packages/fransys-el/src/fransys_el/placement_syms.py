"""One `Sym` per picked function: geometry, footprint, sizes and the facts it is read by."""

from dataclasses import replace
from typing import TYPE_CHECKING

from fransys_layout.core import Box, BoxSpec, Orientation, Pin, Sym
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
from .kit_keys import PickKey, function_of, strip_tag_of, tag_of
from .placement_groups import group_of
from .placement_pins import box_of, nodes_of, pins_of, shape_of, symbol_of
from .placement_sets import drawing_scopes
from .placement_where import where_room
from .write_markings import marking_slots

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping

    from electrical_symbols import Library
    from fransys_layout.core import Size
    from fransys_layout.symbols import LibrarySymbol, Shape
    from fransys_model.derive import Footprints
    from fransys_model.kernel import Id
    from fransys_model.vocab import Function, Unit

    from .placement_env import Env
    from .placement_kit import Pick

__all__ = ["strip_tags", "syms_of"]

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


def _labels(env: Env, symbol: LibrarySymbol, ask: Ask, whole: Size, texts: Mapping[str, str]) -> dict[str, Size]:
    """The label size per set that draws the symbol: the tag text each set's unit prints (`texts`), "" the whole model's."""
    if not (whole.w or whole.h):
        return {"": whole} | dict.fromkeys(texts, whole)  # no tag slot: zero in every set
    one = replace(ask, orientations=("R0",), table=None)  # the label is the text's, whatever the turn or the table
    return {"": whole} | {k: symbol_views(symbol, env.library, replace(one, text=t)).label for k, t in texts.items()}


def _wider(env: Env, symbol: LibrarySymbol, ask: Ask, lead: PickKey, homes: Collection[Id[Unit] | None]) -> tuple[dict[str, Size], ...]:
    """The label sizes again for a where-text page number of 2, 3, ... digits (R1883); none without a where-room."""
    one = replace(ask, orientations=("R0",), table=None)
    texts = {"": tag_of(env.model, lead)} | {u.value: tag_of(env.model, lead, unit=u) for u in homes if u}
    rooms = [where_room(env, function_of(env.model, lead), digits) for digits in range(2, 2 + env.conventions.options.where_digit_rounds)]
    return tuple({k: symbol_views(symbol, env.library, replace(one, text=t + room)).label for k, t in texts.items()} for room in rooms if room)


def _ask(env: Env, lead: PickKey, pick: Pick, pins: tuple[Pin, ...], box: BoxSpec | None) -> Ask:
    """What symdef is asked about `lead`'s symbol drawn as `pick`: its pins, tag text, table and the markings."""
    function = function_of(env.model, lead)
    return Ask(
        BOX if box else PLAIN,
        [p.id for p in pins],
        "tag",
        tag_of(env.model, lead) + where_room(env, function),
        env.conventions.text_height,
        None,
        strip_of(env.model, function_item(env.model, function)) is not None,
        marking_slots(env.model, pick, env.library),
    )


def strip_tags(env: Env) -> dict[str, dict[str, Size]]:
    """Per strip, the size of the tag its runs print once (STRIP-TAG-ONCE), per set like `Sym.labels`, measured at the strip's first terminal."""
    homes = [s.of_unit for s in drawing_scopes(env.model, env.kit) if s.of_unit]
    found: dict[str, dict[str, Size]] = {}
    for lead in env.ids:
        strip = strip_of(env.model, function_item(env.model, function_of(env.model, lead)))
        if strip is None or strip.value in found:
            continue
        pick = env.kit[lead]
        symbol = symbol_of(env, lead, pick)
        shape = shape_of(env, lead, pick, symbol)
        pins = pins_of(env, pick, shape)
        one = replace(_ask(env, lead, pick, pins, box_of(pick, shape, pins)), orientations=("R0",))
        texts = {"": strip_tag_of(env.model, lead)} | {u.value: strip_tag_of(env.model, lead, unit=u) for u in homes}
        found[strip.value] = {k: symbol_views(symbol, env.library, replace(one, text=t)).label for k, t in texts.items()}
    return found


def sym_and_table(env: Env, lead: PickKey, pick: Pick, homes: Collection[Id[Unit] | None] = ()) -> tuple[Sym, Box | None]:
    """The `Sym` of `lead` drawn as `pick`, and its contact table's keep-out (top-left at 0, 0).

    `homes` are the units of the sets that draw it: its label is measured for each as that set prints the tag.
    """
    symbol = symbol_of(env, lead, pick)
    shape = shape_of(env, lead, pick, symbol)
    pins = pins_of(env, pick, shape)
    box = box_of(pick, shape, pins)
    function = function_of(env.model, lead)
    item = function_item(env.model, function)
    strip = strip_of(env.model, item)
    table = _table(_foot(env, function, shape), env.library)
    room = where_room(env, function)
    ask = replace(_ask(env, lead, pick, pins, box), table=table)
    drawn = symbol_views(symbol, env.library, ask)
    sym = Sym(
        id=env.ids[lead],
        group=group_of(env.model, function),
        unit="" if (unit := item_unit(env.model, item)) is None else unit.value,  # empty for the integrating script's own wiring
        labels=_labels(env, symbol, ask, drawn.label, {u.value: tag_of(env.model, lead, unit=u) + room for u in homes if u}),
        pins=pins,
        nodes=nodes_of(shape),
        views=drawn.views,
        box=box,
        row_group=None if strip is None else strip.value,
        item=item.value,
        child_of=env.parents[item].value if item in env.parents else None,
        rank=env.ranks[lead],
        wider=_wider(env, symbol, ask, lead, homes),
    )
    return sym, drawn.table


def syms_of(env: Env, tables: dict[str, Box] | None = None) -> tuple[Sym, ...]:
    """Every `Sym` in function order (`symbol_ids`); `tables` gets the table box of each coil with one."""
    homes: dict[str, set[Id[Unit] | None]] = {}
    for scope in drawing_scopes(env.model, env.kit):
        for sid in scope.symbols:
            homes.setdefault(sid, set()).add(scope.of_unit)
    found = [
        sym_and_table(env, lead, env.kit[lead], homes.get(env.ids[lead], ())) for lead in env.ids
    ]  # env.ids stands in function order (model-0396)
    if tables is not None:
        tables.update({s.id: t for s, t in found if t is not None})
    return tuple(s for s, _ in found)
