"""A contact function with no pole link pairs its pins by `unlinked_poles`; an odd pin stands alone.

The pairing skips earth pins and does not filter by name: a pin never vanishes (model-0128, G3).
"""

import pytest
from plant import Plant

from fransys_model.derive.contact_entries import contact_entries
from fransys_model.kernel import make_id
from fransys_model.vocab import FunctionKind, PartCategory
from fransys_model.vocab.enums import PortRole
from fransys_model.vocab.tables import functions
from fransys_model.vocab.templates import FunctionTemplate, Part, PortTemplate


def _entries(pins: dict[str, PortRole]) -> list[str]:
    """The NO entries' marks of one `contact_no` function with `pins` and no link."""
    plant = Plant()
    part = Part(
        id=make_id(Part, ("blk",)),
        key=("blk",),
        mpn="EXAMPLE-BLK",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.ELECTROMECHANICAL,
        class_code="K",
    )
    template = FunctionTemplate(
        id=make_id(FunctionTemplate, ("blk", "fn")),
        key=("blk", "fn"),
        part=part.id,
        name="fn",
        kind=FunctionKind.CONTACT_NO,
    )
    plant.add(part, template)
    item = plant.item("k", part=part.id)
    function = plant.function(item, "fn", template=template.id, kind=FunctionKind.CONTACT_NO)
    for name, role in pins.items():
        pin = PortTemplate(
            id=make_id(PortTemplate, ("blk", "fn", name)),
            key=("blk", "fn", name),
            function=template.id,
            name=name,
            role=role,
        )
        plant.add(pin)
        plant.port(function, name, template=pin.id)
    model = plant.model()
    no, nc = contact_entries(model, functions(model)[function])
    assert nc == []
    return [mark for _, _, mark in no]


@pytest.mark.parametrize(
    ("pins", "marks"),
    [
        ({"1": PortRole.GENERIC, "2": PortRole.GENERIC, "3": PortRole.GENERIC}, ["1-2", "3"]),
        ({"A": PortRole.GENERIC, "B": PortRole.GENERIC, "C": PortRole.GENERIC}, ["A-B", "C"]),
        ({"1": PortRole.GENERIC, "2": PortRole.GENERIC, "PE": PortRole.PE}, ["1-2"]),
    ],
    ids=["odd digit pin", "odd named pin", "earth pin left out"],
)
def test_unlinked_pins_pair_and_the_odd_pin_is_listed_last(pins, marks) -> None:
    """Catches the odd pin or a non-digit pin vanishing, and an earth pin joining a pole."""
    assert _entries(pins) == marks
