"""The rack-shaped PLC query: a rack's modules in physical order with their channels.

See derive-queries.md.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from fransys_model.kernel import DIGEST_CACHE_SIZE, digest_cached
from fransys_model.vocab.facets.plc import PlcChannelFacet, PlcRequestFacet
from fransys_model.vocab.facets.scaling import ScalingFacet
from fransys_model.vocab.membership import external
from fransys_model.vocab.plc_module import is_plc_module
from fransys_model.vocab.tables import facets_of, functions, items, parts, ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Port, Unit

from .designation import printed_designation
from .facts.children import child_items
from .indexes import build_indexes
from .lookups import channel_devices, require
from .order import plc_channel_tie, plc_module_key
from .rows_plc import ChannelScaling, PlcRackChannel, PlcRackModule

if TYPE_CHECKING:
    from fransys_model.vocab.core import Function
    from fransys_model.vocab.templates import FunctionTemplate, Part

    from .indexes import Indexes


@dataclass(frozen=True, slots=True)
class _Facts:
    """What a channel's field side is read from, looked up once per query."""

    channel_of: frozendict[Id[FunctionTemplate], PlcChannelFacet]
    requests: frozendict[Id[Function], PlcRequestFacet]
    scalings: frozendict[Id[Function], ScalingFacet]
    devices: frozendict[Id[Function], Id[Function]]


def _modules(model: Model, rack: Id[Item]) -> list[tuple[Item, Part]]:
    """The PLC modules of `rack` with their parts, in rack order."""
    found = []
    for child in child_items(model, rack):
        module = items(model)[child]
        if is_plc_module(model, module):
            found.append(
                (module, parts(model)[cast("Id[Part]", module.part)])
            )  # is_plc_module: part is set
    return sorted(found, key=lambda pair: plc_module_key(pair[0]))


def _channel(
    model: Model,
    facts: _Facts,
    spare_stem: str,
    pair: tuple[Id[Function], PlcChannelFacet],
    unit: Id[Unit] | None,
) -> PlcRackChannel:
    """One channel; `spare_stem` is its stem when no bound device and signal name give one."""
    function_id, facet = pair
    all_functions = functions(model)
    device = facts.devices.get(function_id)
    request = None if device is None else facts.requests.get(device)
    scaling = None if device is None else facts.scalings.get(device)
    designation = (
        None
        if device is None
        else printed_designation(model, all_functions[device].item, unit=unit)
    )
    signal_name = None if request is None else request.signal_name
    return PlcRackChannel(
        channel=function_id,
        number=facet.channel,
        signal=facet.signal,
        field_device=device,
        field_device_designation=designation,
        signal_name=signal_name,
        scaling=None
        if scaling is None
        else ChannelScaling(
            unit=scaling.unit,
            raw_min=scaling.raw_min,
            raw_max=scaling.raw_max,
            eng_min=scaling.eng_min,
            eng_max=scaling.eng_max,
        ),
        name_stem=(
            f"{designation}_{signal_name}"
            if designation is not None and signal_name is not None
            else spare_stem
        ),
    )


def _channels(
    model: Model, idx: Indexes, facts: _Facts, module: Item, unit: Id[Unit] | None
) -> tuple[PlcRackChannel, ...]:
    """The module's channels in `plc_channel_tie` order, each built once with its stem."""
    all_functions = functions(model)
    found = []
    for function_id in idx.functions_by_item.get(module.id, ()):
        template = all_functions[function_id].template
        facet = None if template is None else facts.channel_of.get(template)
        if facet is not None:
            found.append((function_id, facet))
    found.sort(key=lambda pair: plc_channel_tie(pair[1].channel, all_functions[pair[0]]))
    head = printed_designation(model, module.id, unit=unit)
    return tuple(
        _channel(model, facts, f"{head}_{nr}", pair, unit) for nr, pair in enumerate(found)
    )


def _rack_module(
    model: Model, idx: Indexes, facts: _Facts, found: tuple[Item, Part], unit: Id[Unit] | None
) -> PlcRackModule:
    module, part = found
    designation = printed_designation(model, module.id, unit=unit)
    return PlcRackModule(
        module=module.id,
        designation=designation,
        mpn=part.mpn,
        description=part.description,
        position=module.position,
        channels=_channels(model, idx, facts, module, unit),
    )


def plc_rack_modules(
    model: Model, rack: Id[Item], *, unit: Id[Unit] | None = None
) -> tuple[PlcRackModule, ...]:
    """One `PlcRackModule` per PLC module of `rack`, in physical rack order.

    The modules are the children of `rack` by `parent` whose `Part` has category `PLC_MODULE`; a
    module with no channel (a coupler, an end module) has `channels=()`. They order by `position`
    (integers ascending, `None` last), then the module's own tag in natural order
    (`plc_module_key`), the order `allocate_plc` serves them in; `installed` is ignored. A module's
    channels are the functions whose template carries a `plc_channel`, bound or spare, ordered by
    `plc_channel_tie`. The field device is read as `plc_channel_rows` reads it; `scaling` is its
    `scaling` facet, `None` for a spare channel or a device without one.

    `unit` prints the designations as that unit's own document does; `None` the full form.

    Raises:
        SchemaError: `rack` is not an item of `model`, or a module or device has no designation.
    """
    require(items(model).get(rack), "item", rack)
    idx = build_indexes(model)
    facts = _Facts(
        channel_of=frozendict(
            {facet.subject: facet for facet in facets_of(model, PlcChannelFacet).values()}
        ),
        requests=frozendict(
            {facet.subject: facet for facet in facets_of(model, PlcRequestFacet).values()}
        ),
        scalings=frozendict(
            {facet.subject: facet for facet in facets_of(model, ScalingFacet).values()}
        ),
        devices=frozendict(channel_devices(model)),
    )
    return tuple(_rack_module(model, idx, facts, found, unit) for found in _modules(model, rack))


@digest_cached(DIGEST_CACHE_SIZE)
def channel_pins(model: Model) -> frozenset[Id[Port]]:
    """The pins that are a channel: a PLC channel template's, and every pin of a part-less device.

    The second case is an external item with no part: its channels are unknown, so each pin is one.
    """
    templates = {facet.subject for facet in facets_of(model, PlcChannelFacet).values()}
    all_functions, all_items = functions(model), items(model)
    found = set()
    for pin in ports(model).values():
        function = all_functions[pin.function]
        item = all_items[function.item]
        if function.template in templates or (item.part is None and external(model, item.id)):
            found.add(pin.id)
    return frozenset(found)
