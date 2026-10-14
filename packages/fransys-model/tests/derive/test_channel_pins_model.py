"""`channel_pins`: a PLC channel template's pins and every pin of a part-less external item.

Invented items: a module with one channel function, a part-less external device, a part-less
device that is not external, and an external device with a part (layout-0208, point FIX-A).
"""

from cable_drawing_builders import device, edit
from plant import Plant

from fransys_model.derive import channel_pins
from fransys_model.kernel import make_id
from fransys_model.vocab.enums import FunctionKind, PartCategory, SignalType
from fransys_model.vocab.facets.plc import PlcChannelFacet
from fransys_model.vocab.templates import FunctionTemplate, Part


def test_channel_pins_are_template_channels_and_partless_external_pins() -> None:
    """Both cases are in; a part-less internal device and a parted external device are out."""
    plant = Plant()
    part = Part(
        id=make_id(Part, ("mod",)),
        key=("mod",),
        mpn="EXAMPLE-mod",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.PLC_MODULE,
        class_code="A",
    )
    template = FunctionTemplate(
        id=make_id(FunctionTemplate, ("mod", "ch1")),
        key=("mod", "ch1"),
        part=part.id,
        name="ch1",
        kind=FunctionKind.PLC_CHANNEL,
    )
    facet = PlcChannelFacet(
        id=make_id(PlcChannelFacet, ("mod", "ch1", "facet")),
        key=("mod", "ch1", "facet"),
        subject=template.id,
        signal=SignalType.DI,
        channel=1,
    )
    plant.add(part, template, facet)
    module = plant.item("module", designation="A1", part=part.id)
    channel = plant.function(module, "ch1", template=template.id, kind=FunctionKind.PLC_CHANNEL)
    channel_pin = plant.port(channel, "1")
    _, external = device(plant, "ext", "X1", "a", "b", external=True)
    _, internal = device(plant, "int", "X2", "a")
    parted, parted_pins = device(plant, "parted", "X3", "a", external=True)
    edit(plant, parted, part=part.id)

    assert channel_pins(plant.model()) == {channel_pin, *external.values()}
    assert not set(internal.values()) & channel_pins(plant.model())
    assert not set(parted_pins.values()) & channel_pins(plant.model())
