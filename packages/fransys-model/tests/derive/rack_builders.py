"""Invented PLC racks for the `plc_tables` tests: controllers, modules and a loose item."""

import dataclasses
from typing import TYPE_CHECKING

from plant import Plant

from fransys_model.kernel import make_id
from fransys_model.vocab.enums import FunctionKind, PartCategory, SignalType
from fransys_model.vocab.facets.plc import PlcChannelFacet
from fransys_model.vocab.templates import FunctionTemplate, Part
lazy from fransys_model.vocab.core import Item

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model


@dataclasses.dataclass(frozen=True)
class Racks:
    """The frozen model and the items the tests name."""

    model: Model
    first_rack: Id[Item]
    first_rack_module: Id[Item]
    rack: Id[Item]
    modules_in_rack_order: tuple[Id[Item], ...]
    coupler: Id[Item]
    loose: Id[Item]


def _part(plant: Plant, key: str, category: PartCategory, channels: int) -> Id[Part]:
    """A part with `channels` DI channel templates numbered from 1."""
    part = Part(
        id=make_id(Part, (key,)),
        key=(key,),
        mpn=f"EXAMPLE-{key}",
        manufacturer="Example Co",
        description="Invented",
        category=category,
        class_code="A",
    )
    plant.add(part)
    for number in range(1, channels + 1):
        template = FunctionTemplate(
            id=make_id(FunctionTemplate, (key, f"ch{number}")),
            key=(key, f"ch{number}"),
            part=part.id,
            name=f"ch{number}",
            kind=FunctionKind.PLC_CHANNEL,
        )
        facet = PlcChannelFacet(
            id=make_id(PlcChannelFacet, (key, f"ch{number}", "facet")),
            key=(key, f"ch{number}", "facet"),
            subject=template.id,
            signal=SignalType.DI,
            channel=number,
        )
        plant.add(template, facet)
    return part.id


def _channels(plant: Plant, item: Id[Item], part: Id[Part]) -> None:
    """The channel functions of `item`, created highest number first."""
    templates = [
        one for one in plant.records if isinstance(one, FunctionTemplate) and one.part == part
    ]
    for template in reversed(templates):
        plant.function(item, template.name, template=template.id, kind=FunctionKind.PLC_CHANNEL)


def _position(plant: Plant, item: Id[Item], position: int) -> None:
    """Give the added item `item` a `position`."""
    plant.records = [
        dataclasses.replace(one, position=position) if one.id == item else one
        for one in plant.records
    ]


def build_racks() -> Racks:
    """Two controllers, a loose item, and modules whose key order is not their rack order.

    Controller `-C1` (key `a_rack`) has modules `m_b` at position 1 and `m_a` at position 2 and a
    coupler at 0 with no channel; `-C0` (key `zz_rack`) has one module: designation order puts it
    first, key order last. `-X9` is in no rack.
    """
    plant = Plant()
    controller = _part(plant, "ctrl", PartCategory.GENERIC, 1)
    module = _part(plant, "mod", PartCategory.PLC_MODULE, 2)
    coupler_part = _part(plant, "coupler", PartCategory.PLC_MODULE, 0)
    loose_part = _part(plant, "loose", PartCategory.GENERIC, 1)
    rack = plant.item("a_rack", designation="C1", part=controller)
    first_rack = plant.item("zz_rack", designation="C0", part=controller)
    m_a = plant.item("m_a", designation="A2", part=module, parent=rack)
    m_b = plant.item("m_b", designation="A1", part=module, parent=rack)
    coupler = plant.item("m_c", designation="A0", part=coupler_part, parent=rack)
    first_module = plant.item("only", designation="A1", part=module, parent=first_rack)
    loose = plant.item("loose", designation="X9", part=loose_part)
    for item, position in ((m_a, 2), (m_b, 1), (coupler, 0)):
        _position(plant, item, position)
    for item, part in (
        (rack, controller),
        (first_rack, controller),
        (m_a, module),
        (m_b, module),
        (first_module, module),
        (loose, loose_part),
    ):
        _channels(plant, item, part)
    return Racks(plant.model(), first_rack, first_module, rack, (m_b, m_a), coupler, loose)
