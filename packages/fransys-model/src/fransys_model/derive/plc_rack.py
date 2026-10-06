"""The rack-shaped PLC query: a rack's modules in physical order with their channels.

See derive-queries.md.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from fransys_model.vocab.enums import PartCategory
from fransys_model.vocab.facets.plc import PlcChannelFacet, PlcRequestFacet
from fransys_model.vocab.facets.scaling import ScalingFacet
from fransys_model.vocab.tables import facets_of, functions, items, parts
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Unit

from .designation import printed_designation
from .indexes import build_indexes
from .lookups import channel_devices, position_rank, require
from .rows import ChannelScaling, PlcRackChannel, PlcRackModule

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


def is_plc_module(model: Model, item: Item) -> bool:
    """Whether `item`'s part has category `PLC_MODULE`: the one test of what a rack holds.

    A rack is an item with at least one such child; `plc_rack_modules` lists them.
    """
    return item.part is not None and parts(model)[item.part].category is PartCategory.PLC_MODULE


def _modules(model: Model, idx: Indexes, rack: Id[Item]) -> list[tuple[Item, Part]]:
    """The PLC modules of `rack` with their parts, in rack order."""
    found = []
    for child in idx.children_by_item.get(rack, ()):
        module = items(model)[child]
        if is_plc_module(model, module):
            found.append(
                (module, parts(model)[cast("Id[Part]", module.part)])
            )  # is_plc_module: part is set
    return sorted(found, key=lambda pair: (position_rank(pair[0]), pair[0].key))


def _channels(
    model: Model, idx: Indexes, facts: _Facts, module: Item, unit: Id[Unit] | None
) -> tuple[PlcRackChannel, ...]:
    all_functions = functions(model)
    channels = []
    for function_id in idx.functions_by_item.get(module.id, ()):
        template = all_functions[function_id].template
        facet = None if template is None else facts.channel_of.get(template)
        if facet is None:
            continue
        device = facts.devices.get(function_id)
        request = None if device is None else facts.requests.get(device)
        scaling = None if device is None else facts.scalings.get(device)
        channels.append(
            PlcRackChannel(
                channel=function_id,
                number=facet.channel,
                signal=facet.signal,
                field_device=device,
                field_device_designation=(
                    None
                    if device is None
                    else printed_designation(model, all_functions[device].item, unit=unit)
                ),
                signal_name=None if request is None else request.signal_name,
                scaling=None
                if scaling is None
                else ChannelScaling(
                    unit=scaling.unit,
                    raw_min=scaling.raw_min,
                    raw_max=scaling.raw_max,
                    eng_min=scaling.eng_min,
                    eng_max=scaling.eng_max,
                ),
            )
        )
    return tuple(sorted(channels, key=lambda channel: (channel.number, channel.channel)))


def plc_rack_modules(
    model: Model, rack: Id[Item], *, unit: Id[Unit] | None = None
) -> tuple[PlcRackModule, ...]:
    """One `PlcRackModule` per PLC module of `rack`, in physical rack order.

    The modules are the children of `rack` by `parent` whose `Part` has category `PLC_MODULE`; a
    module with no channel (a coupler, an end module) has `channels=()`. They order by `position`
    (integers ascending, `None` last), then authoring key and id, the order `allocate_plc` serves
    them in; `installed` is ignored. A module's channels are the functions whose template carries a
    `plc_channel`, bound or spare, ordered by `(plc_channel.channel, function id)`. The field device
    is read as `plc_channel_rows` reads it; `scaling` is its `scaling` facet, `None` for a spare
    channel or a device without one.

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
    return tuple(
        PlcRackModule(
            module=module.id,
            designation=printed_designation(model, module.id, unit=unit),
            mpn=part.mpn,
            description=part.description,
            position=module.position,
            channels=_channels(model, idx, facts, module, unit),
        )
        for module, part in _modules(model, idx, rack)
    )
