"""Invented PLC racks for the `plc_rack_modules` tests: modules under a rack item."""

from decimal import Decimal
from typing import TYPE_CHECKING

from fransys_model.kernel import Id, make_id
from fransys_model.vocab.core import Function, Item
from fransys_model.vocab.enums import FunctionKind, PartCategory, SignalType
from fransys_model.vocab.facets.plc import PlcChannelFacet
from fransys_model.vocab.facets.scaling import ScalingFacet
from fransys_model.vocab.templates import FunctionTemplate, Part

if TYPE_CHECKING:
    from plant import Plant


def make_module(  # noqa: PLR0913 -- one builder for every module shape a test needs
    plant: Plant,
    rack: Id[Item],
    key: str,
    *,
    part: str,
    signals: tuple[SignalType, ...],
    position: int | None,
    designation: str | None,
    category: PartCategory = PartCategory.PLC_MODULE,
    installed: bool = True,
) -> tuple[Id[Item], list[Id[Function]]]:
    """A module item `key` under `rack` of the part `part`, one channel function per signal.

    The part, its templates and its `plc_channel` facets are added once, so two modules of one
    `part` share them; `signals` is read the first time.
    """
    part_id = make_id(Part, (part,))
    if not plant.has(part_id):
        plant.add(
            Part(
                id=part_id,
                key=(part,),
                mpn=f"MPN-{part}",
                manufacturer="Example Co",
                description=f"Invented {part}",
                category=category,
                class_code="A",
            )
        )
        for number, signal in enumerate(signals, start=1):
            template = FunctionTemplate(
                id=make_id(FunctionTemplate, (part, f"ch{number}")),
                key=(part, f"ch{number}"),
                part=part_id,
                name=f"ch{number}",
                kind=FunctionKind.PLC_CHANNEL,
            )
            facet = PlcChannelFacet(
                id=make_id(PlcChannelFacet, (part, f"ch{number}", "facet")),
                key=(part, f"ch{number}", "facet"),
                subject=template.id,
                signal=signal,
                channel=number,
            )
            plant.add(template, facet)
    module = make_id(Item, (key,))
    plant.add(
        Item(
            id=module,
            key=(key,),
            part=part_id,
            parent=rack,
            position=position,
            tag=designation,
            description="Invented",
            installed=installed,
        )
    )
    functions = [
        plant.function(
            module, f"ch{number}", template=make_id(FunctionTemplate, (part, f"ch{number}"))
        )
        for number in range(1, len(signals) + 1)
    ]
    return module, functions


def scale(plant: Plant, device: Id[Function], key: str) -> ScalingFacet:
    """A `scaling` facet of `device`: raw 4..20 mA to 0..100 percent."""
    facet = ScalingFacet(
        id=make_id(ScalingFacet, (key, "scaling")),
        key=(key, "scaling"),
        subject=device,
        unit="percent",
        raw_min=4,
        raw_max=20,
        eng_min=Decimal(0),
        eng_max=Decimal(100),
    )
    plant.add(facet)
    return facet
