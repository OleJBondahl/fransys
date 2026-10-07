"""Report queries: PLC channels, cables, wire labels and the designation list.

See design/derive-queries.md.

`bom_lines` and its unit scope are in `derive.bom`. Every row field a human reads is rendered
by `derive.designation`, so a query over an item whose `designation` is still `None` (and which
is not a terminal) raises `SchemaError`: run `numbering` first. A query leaves out what it
cannot render instead of defaulting it (decision 0021).
"""

from typing import TYPE_CHECKING

from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, SchemaError, digest_cached
from fransys_model.vocab.enums import ConductorKind
from fransys_model.vocab.facets.cable import CableProductFacet, CoreFacet
from fransys_model.vocab.facets.plc import PlcChannelFacet, PlcRequestFacet
from fransys_model.vocab.facets.wire import WireFacet
from fransys_model.vocab.tables import conductors, facets_of, functions, items
from fransys_model.vocab.tables import units as units_table
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.connectivity import Conductor
lazy from fransys_model.vocab.core import Item, Unit

from .cable_end_rank import cable_end_rank
from .designation import (
    bom_sort_key,
    end_outside_nested_unit,
    is_own_unit_root,
    port_designation,
    printed_designation,
    reference_designation,
    takes_parents_designation,
    unit_list_context,
)
from .drawing_text import port_designation_in, wire_text
from .indexes import Indexes, build_indexes
from .list_cells import CELL_SEPARATOR
from .lookups import (
    cable_end_owner,
    channel_devices,
    item_description,
    item_of_port,
    require,
    unit_chain,
)
from .natural_order import natural_key
from .rows import CableRow, DesignationRow, PlcChannelRow, WireRow
from .structure import boards
from .wire_ends import ordered_wire_ends
from .wiring import terminal_strips

if TYPE_CHECKING:
    from fransys_model.vocab.core import Function, Port
    from fransys_model.vocab.templates import Part


@digest_cached(DIGEST_CACHE_SIZE)
def _cable_products_by_part(model: Model) -> frozendict[Id[Part], CableProductFacet]:
    """Every `CableProductFacet` by the part it describes, built once per model digest.

    The facet's `unique=True` allows at most one per part, so no first-match tie-break is needed.
    """
    return frozendict(
        {facet.subject: facet for facet in facets_of(model, CableProductFacet).values()}
    )


@digest_cached(DIGEST_CACHE_SIZE)
def _cores_by_cable(model: Model) -> frozendict[Id[Item], tuple[tuple[Conductor, CoreFacet], ...]]:
    """Every core conductor and its `CoreFacet`, grouped by the cable (`carrier`) it belongs to.

    Built once per model digest from `ConductorKind.CORE` conductors with a carrier and facet.
    """
    core_of = {facet.subject: facet for facet in facets_of(model, CoreFacet).values()}
    grouped: dict[Id[Item], list[tuple[Conductor, CoreFacet]]] = {}
    for conductor in conductors(model).values():
        facet = core_of.get(conductor.id)
        if conductor.kind is not ConductorKind.CORE or conductor.carrier is None or facet is None:
            continue
        grouped.setdefault(conductor.carrier, []).append((conductor, facet))
    return frozendict({cable: tuple(pairs) for cable, pairs in grouped.items()})


def _require_unit(model: Model, unit: Id[Unit] | None) -> None:
    """Refuse `unit` if it names no `Unit` of `model`; `None` is always fine (units spec U6)."""
    if unit is not None:
        require(units_table(model).get(unit), "unit", unit)


def _item_belongs(model: Model, item_id: Id[Item], unit: Id[Unit]) -> bool:
    """Whether `item_id` is directly a member of `unit` (units spec U6): `item.unit == unit`.

    Direct membership only, never `unit_subtree`: an item of a nested unit belongs to that
    nested unit alone, never to its ancestor.
    """
    return items(model)[item_id].unit == unit


def unit_strips(model: Model, unit: Id[Unit]) -> tuple[Id[Item], ...]:
    """The terminal strips `unit` owns directly, in designation order, never a nested unit's.

    The strips of `terminal_strips` whose `item.unit` is `unit`; one test of a unit's own strips.
    """
    return tuple(strip for strip in terminal_strips(model) if _item_belongs(model, strip, unit))


def unit_boards(model: Model, unit: Id[Unit]) -> tuple[Id[Item], ...]:
    """The boards `unit` owns directly, in designation order, never a nested unit's.

    The boards of `boards` whose `item.unit` is `unit`; the one test of a unit's own boards.
    """
    return tuple(board for board in boards(model) if _item_belongs(model, board, unit))


def _lowest_common_unit(model: Model, a: Id[Unit] | None, b: Id[Unit] | None) -> Id[Unit] | None:
    """The lowest unit whose subtree holds both `a` and `b`; `None` if either is `None`.

    Either end with no unit at all means the conductor belongs to no unit (units spec U6).
    """
    if a is None or b is None:
        return None
    if a == b:
        return a
    chain_b = set(unit_chain(model, b))
    return next((candidate for candidate in unit_chain(model, a) if candidate in chain_b), None)


def _conductor_unit(model: Model, conductor: Conductor) -> Id[Unit] | None:
    """The unit `conductor` belongs to, or `None`.

    A `core` conductor belongs to its cable item's own unit, never computed from its ends.
    Any other belongs to the lowest unit whose subtree holds both ends' items.
    """
    if conductor.kind is ConductorKind.CORE and conductor.carrier is not None:
        return items(model)[conductor.carrier].unit
    a_unit = items(model)[item_of_port(model, conductor.a)].unit
    b_unit = items(model)[item_of_port(model, conductor.b)].unit
    return _lowest_common_unit(model, a_unit, b_unit)


def _conductor_belongs(model: Model, conductor: Conductor, unit: Id[Unit]) -> bool:
    """Whether `conductor` belongs to `unit` (units spec U6): `_conductor_unit(...) == unit`."""
    return _conductor_unit(model, conductor) == unit


def _wired_to(
    model: Model,
    idx: Indexes,
    channel: Id[Function],
    context: Id[AspectNode] | None,
    unit: Id[Unit] | None,
) -> str | None:
    """Where the builder wires `channel`'s pins: its far ends as printed, `None` for none.

    The far end of every conductor at every port of `channel`, via `_end_text` (blank: left out).
    Distinct ends print once each, sorted by `bom_sort_key` on the end's item, joined.
    """
    texts: dict[str, Id[Item]] = {}
    for port in idx.ports_by_function.get(channel, ()):
        for conductor_id in idx.conductors_by_port.get(port, ()):
            conductor = conductors(model)[conductor_id]
            far = conductor.b if conductor.a == port else conductor.a
            if text := _end_text(model, far, context, unit):
                texts.setdefault(text, item_of_port(model, far))
    if not texts:
        return None
    ordered = sorted(texts.items(), key=lambda pair: bom_sort_key(model, pair[1]))
    return CELL_SEPARATOR.join(text for text, _ in ordered)


def plc_channel_rows(
    model: Model, *, unit: Id[Unit] | None = None, context: Id[AspectNode] | None = None
) -> tuple[PlcChannelRow, ...]:
    """One `PlcChannelRow` per PLC channel `Function`, sorted by `(channel_designation, id)`.

    `wired_to` is the far end of every conductor at the channel's ports.

    Args:
        model: The frozen model to read.
        unit: Keep only channels of this unit; `None` keeps all.
        context: The location node the list is printed for; ignored once `unit` has one.

    Returns:
        One `PlcChannelRow` per PLC channel function, sorted.

    Raises:
        SchemaError: a module or device has no designation, or `unit` is no unit of `model`.
    """
    _require_unit(model, unit)
    context = unit_list_context(model, unit, context)
    idx = build_indexes(model)
    channel_of = {facet.subject: facet for facet in facets_of(model, PlcChannelFacet).values()}
    requests = {facet.subject: facet for facet in facets_of(model, PlcRequestFacet).values()}
    devices = channel_devices(model)
    all_functions = functions(model)
    rows = []
    for function in all_functions.values():
        facet = channel_of.get(function.template)
        if facet is None:
            continue
        if unit is not None and not _item_belongs(model, function.item, unit):
            continue
        device = devices.get(function.id)
        device_item = None if device is None else all_functions[device].item
        request = None if device is None else requests.get(device)
        rows.append(
            PlcChannelRow(
                channel=function.id,
                channel_designation=(
                    f"{printed_designation(model, function.item, unit=unit)}:{facet.channel}"
                ),
                signal=facet.signal,
                wired_to=_wired_to(model, idx, function.id, context, unit),
                field_device=device,
                field_device_designation=(
                    None
                    if device_item is None or end_outside_nested_unit(model, device_item, unit)
                    else printed_designation(model, device_item, unit=unit)
                ),
                signal_name=None if request is None else request.signal_name,
            )
        )
    return tuple(sorted(rows, key=lambda row: (natural_key(row.channel_designation), row.channel)))


def _oriented_ends(model: Model, a: Id[Port], b: Id[Port]) -> tuple[Id[Port], Id[Port]]:
    """`(a, b)`, swapped if needed so the first port's end outranks the second's.

    A `Conductor`'s `a`/`b` are in port-id order, so a core's physical direction is derived here.
    Shared by `cable_rows` and `derive.harness`, so every output agrees on which end is first.
    """
    rank_a = cable_end_rank(model, cable_end_owner(model, item_of_port(model, a)))
    rank_b = cable_end_rank(model, cable_end_owner(model, item_of_port(model, b)))
    return (a, b) if rank_a <= rank_b else (b, a)


def _product_colours(model: Model, cable: Id[Item]) -> tuple[str, ...]:
    """The `core_colours` of `cable`'s part's `cable_product`, `()` when it has none.

    Reads `_cable_products_by_part`, an `Id[Part]`-keyed index built once per model digest.
    """
    part = items(model)[cable].part
    if part is None:
        return ()
    facet = _cable_products_by_part(model).get(part)
    return () if facet is None else facet.core_colours


def _colour_at(colours: tuple[str, ...], index: int, conductor: Conductor) -> str:
    """`colours[index - 1]`; an index outside the product is a `SchemaError` (SC4)."""
    if not 1 <= index <= len(colours):
        msg = (
            f"core {index} is outside its cable product's {len(colours)} core colour(s), "
            f"so it has no colour"
        )
        raise SchemaError(msg, kind="conductor", record_id=conductor.id)
    return colours[index - 1]


def core_colour(model: Model, conductor: Id[Conductor]) -> str:
    """The colour of core `conductor`: its carrier's `core_colours[index - 1]`.

    The one reader of a core's colour: the facet holds only the index, and the colour is the cable
    product's fact. `cable_rows`, the harness rows and wireviz read it here.

    Args:
        model: The frozen model to read.
        conductor: The core conductor whose colour to render.

    Returns:
        The core's colour, an IEC 60757 code (or code pair).

    Raises:
        SchemaError: `conductor` is not a core of a cable, or has no `core` facet or product entry.
    """
    record = require(conductors(model).get(conductor), "conductor", conductor)
    if record.kind is not ConductorKind.CORE or record.carrier is None:
        msg = "a conductor that is not a cable core has no core colour"
        raise SchemaError(msg, kind="conductor", record_id=conductor)
    for facet in facets_of(model, CoreFacet).values():
        if facet.subject == conductor:
            return _colour_at(_product_colours(model, record.carrier), facet.index, record)
    msg = "a core with no `core` facet has no index, so no colour"
    raise SchemaError(msg, kind="conductor", record_id=conductor)


def cable_rows(
    model: Model, cable: Id[Item], *, unit: Id[Unit] | None = None
) -> tuple[CableRow, ...]:
    """One `CableRow` per core of `cable`, sorted by `(core.index, conductor id)`.

    Cores are the `core`-kind conductors naming `cable` as `carrier`; the colour is `core_colour`'s.

    Args:
        model: The frozen model to read.
        cable: The cable item whose cores to list.
        unit: The unit whose own document draws the cable, keyword-only; `None` is the whole model.

    Returns:
        One `CableRow` per core of `cable`, sorted.

    Raises:
        SchemaError: `cable` is no item, an end has no designation, or `unit` is no unit of `model`.
    """
    require(items(model).get(cable), "item", cable)
    _require_unit(model, unit)
    context = unit_list_context(model, unit, None)

    def end_text(port: Id[Port]) -> str:
        if unit is None:
            return port_designation(model, port)
        return _end_text(model, port, context, unit)

    colours = _product_colours(model, cable)
    rows = []
    for conductor, facet in _cores_by_cable(model).get(cable, ()):
        end_a, end_b = _oriented_ends(model, conductor.a, conductor.b)
        rows.append(
            CableRow(
                cable=cable,
                cable_designation=printed_designation(model, cable, unit=unit),
                index=facet.index,
                colour=_colour_at(colours, facet.index, conductor),
                conductor=conductor.id,
                end_a=end_a,
                end_a_designation=end_text(end_a),
                end_b=end_b,
                end_b_designation=end_text(end_b),
            )
        )
    return tuple(sorted(rows, key=lambda row: (row.index, row.conductor)))


def _end_text(
    model: Model, port: Id[Port], context: Id[AspectNode] | None, unit: Id[Unit] | None
) -> str:
    """One wire-label end as printed: `""` outside a nested `unit`, else `port_designation_in`."""
    if end_outside_nested_unit(model, item_of_port(model, port), unit):
        return ""
    return port_designation_in(model, port, context, unit=unit)


def _wire_row(
    model: Model,
    conductor: Conductor,
    facet: WireFacet,
    context: Id[AspectNode] | None,
    unit: Id[Unit] | None,
) -> WireRow:
    end_from, end_to = ordered_wire_ends(model, conductor.a, conductor.b)
    return WireRow(
        conductor=conductor.id,
        from_=_end_text(model, end_from, context, unit),
        to=_end_text(model, end_to, context, unit),
        colour=facet.colour,
        cross_section_mm2=facet.gauge_mm2,
        label=wire_text(model, conductor.id, unit=unit),
    )


def wire_rows(
    model: Model, *, unit: Id[Unit] | None = None, context: Id[AspectNode] | None = None
) -> tuple[WireRow, ...]:
    """One `WireRow` per `wire`-faceted conductor of kind `WIRE`, sorted by `(from, to, id)`.

    A jumper, a cable core and a link never gets a row. `from`/`to` are the ends as
    the list prints them (`unit` and `context` act the same); `label` is `wire_text`.
    """
    _require_unit(model, unit)
    context = unit_list_context(model, unit, context)
    wire_of = {facet.subject: facet for facet in facets_of(model, WireFacet).values()}
    rows = [
        _wire_row(model, conductor, wire_of[conductor.id], context, unit)
        for conductor in conductors(model).values()
        if conductor.id in wire_of
        and conductor.kind is ConductorKind.WIRE
        and (unit is None or _conductor_belongs(model, conductor, unit))
    ]
    return tuple(sorted(rows, key=lambda row: (row.from_, row.to, row.conductor)))


def designation_list(model: Model, *, unit: Id[Unit] | None = None) -> tuple[DesignationRow, ...]:
    """One `DesignationRow` per `Item`, terminals included, sorted by `(designation, id)`.

    `designation` is `printed_designation` (`"-X1:L1:1"`, `"-K1"`); `reference` is
    `reference_designation`. An accessory (`takes_parents_designation`) has no row.

    Args:
        model: The frozen model to read.
        unit: Keep only rows of this unit, keyword-only; its sole root has no row.

    Returns:
        One `DesignationRow` per item, sorted by `(designation, id)`.

    Raises:
        SchemaError: an item has no designation, or `unit` names no unit of `model`.
    """
    _require_unit(model, unit)
    rows = [
        DesignationRow(
            item=item.id,
            designation=printed_designation(model, item.id, unit=unit),
            reference=reference_designation(model, item.id, unit=unit),
            description=item_description(model, item.id),
        )
        for item in items(model).values()
        if (unit is None or _item_belongs(model, item.id, unit))
        and not takes_parents_designation(model, item.id)
        and not is_own_unit_root(model, item.id, unit)
    ]
    return tuple(sorted(rows, key=lambda row: (natural_key(row.designation), row.item)))
