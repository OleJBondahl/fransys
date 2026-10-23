"""The PLC channel list: one row per pin of each PLC channel, in the list order.

Every row field a human reads is rendered by `derive.designation`; a missing designation raises
`SchemaError`: run `numbering` first (decision 0021).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_model.derive.facts.roles import plc_channel_facets
from fransys_model.vocab.facets.plc import PlcChannelFacet, PlcRequestFacet
from fransys_model.vocab.tables import conductors, facets_of, functions
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.core import Item, Unit

from .designation import end_outside_nested_unit, printed_designation, unit_list_context
from .indexes import Indexes, build_indexes
from .list_cells import CELL_SEPARATOR
from .lookups import channel_devices, item_of_port
from .order import bom_sort_key, plc_channel_key, plc_racks
from .plc_channel_text import channel_pin_designations
from .report_scope import _item_belongs, _require_unit
from .rows_plc import PlcChannelRow
from .texts.context import PrintContext
from .texts.end_text import FAR_END, end_text

if TYPE_CHECKING:
    from fransys_model.vocab.core import Function, Port


def _wired_to(
    model: Model,
    idx: Indexes,
    port: Id[Port],
    context: Id[AspectNode] | None,
    unit: Id[Unit] | None,
) -> str | None:
    """Where the builder wires `port`: its far ends as printed, `None` for none.

    The far end of every conductor at `port`, via `end_text` (blank: left out).
    Distinct ends print once each, sorted by `bom_sort_key` on the end's item, joined.
    """
    texts: dict[str, Id[Item]] = {}
    for conductor_id in idx.conductors_by_port.get(port, ()):
        conductor = conductors(model)[conductor_id]
        far = conductor.b if conductor.a == port else conductor.a
        if text := end_text(model, far, FAR_END, PrintContext(reading=unit, location=context)):
            texts.setdefault(text, item_of_port(model, far))
    if not texts:
        return None
    ordered = sorted(texts.items(), key=lambda pair: bom_sort_key(model, pair[1]))
    return CELL_SEPARATOR.join(text for text, _ in ordered)


@dataclass(frozen=True, slots=True)
class _PlcScope:
    """What every row of one `plc_channel_pairs` call reads, looked up once."""

    model: Model
    idx: Indexes
    context: Id[AspectNode] | None
    unit: Id[Unit] | None
    devices: dict[Id[Function], Id[Function]]
    requests: dict[Id[Function], PlcRequestFacet]


def _plc_pin_rows(
    scope: _PlcScope, function: Function, facet: PlcChannelFacet
) -> tuple[PlcChannelRow, ...]:
    """One `PlcChannelRow` per pin of channel `function`, in pin order (`facet`: its template's)."""
    model, unit = scope.model, scope.unit
    device = scope.devices.get(function.id)
    device_item = None if device is None else functions(model)[device].item
    request = None if device is None else scope.requests.get(device)
    device_designation = (
        None
        if device_item is None or end_outside_nested_unit(model, device_item, unit)
        else printed_designation(model, device_item, unit=unit)
    )
    pins = channel_pin_designations(model, scope.idx, function.id, unit)
    return tuple(
        PlcChannelRow(
            channel=function.id,
            port=port,
            pin=pin,
            channel_name=str(facet.channel),
            signal=facet.signal,
            wired_to=_wired_to(model, scope.idx, port, scope.context, unit),
            field_device=device,
            field_device_designation=device_designation,
            signal_name=None if request is None else request.signal_name,
        )
        for port, pin in pins
    )


def plc_channel_pairs(
    model: Model, *, unit: Id[Unit] | None = None, context: Id[AspectNode] | None = None
) -> tuple[tuple[Id[Item], PlcChannelRow], ...]:
    """Each PLC channel's carrying item and row, in the list order (`plc_channel_key`, L4).

    `plc_channel_rows` and `plc_tables` both read this, so the CSV and the PDF share one order.
    """
    _require_unit(model, unit)
    context = unit_list_context(model, unit, context)
    scope = _PlcScope(
        model,
        build_indexes(model),
        context,
        unit,
        channel_devices(model),
        {one.subject: one for one in facets_of(model, PlcRequestFacet).values()},
    )
    channel_of = plc_channel_facets(model)
    racks = plc_racks(model)
    keyed = []
    for function in functions(model).values():
        facet = channel_of.get(function.template)
        if facet is None or (unit is not None and not _item_belongs(model, function.item, unit)):
            continue
        key = plc_channel_key(model, racks, function.item, facet.channel, function)
        keyed.extend((key, function.item, row) for row in _plc_pin_rows(scope, function, facet))
    return tuple((item, row) for _, item, row in sorted(keyed, key=lambda one: one[0]))


def plc_channel_rows(
    model: Model, *, unit: Id[Unit] | None = None, context: Id[AspectNode] | None = None
) -> tuple[PlcChannelRow, ...]:
    """One `PlcChannelRow` per pin of each PLC channel `Function`, in the PLC list's table order.

    The order is `plc_channel_key`: controllers by designation, each one's own channels
    then its modules in rack order, last the channels on items in no rack. `wired_to` is the far
    end of every conductor at that pin's port. `unit` keeps only channels of that unit;
    `context` is the location node the list is printed for, ignored once `unit` has one.

    Raises:
        SchemaError: a module or device has no designation, or `unit` is no unit of `model`.
    """
    return tuple(row for _, row in plc_channel_pairs(model, unit=unit, context=context))
