"""`unit_racks` (model-0280): the id-sorted racks of a unit, or of every unit with `None`."""

from plant import Plant

from fransys_model.derive import unit_racks
from fransys_model.kernel import make_id
from fransys_model.vocab.enums import PartCategory
from fransys_model.vocab.templates import Part


def _module_part(plant: Plant) -> Part:
    part = Part(
        id=make_id(Part, ("mod",)),
        key=("mod",),
        mpn="EXAMPLE-mod",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.PLC_MODULE,
        class_code="A",
    )
    plant.add(part)
    return part


def test_racks_are_filtered_by_unit_and_sorted_by_id() -> None:
    plant = Plant()
    part = _module_part(plant)
    one, two = plant.unit("u1"), plant.unit("u2")
    racks = {}
    for key, unit in (("r_b", one), ("r_a", one), ("r_c", two)):
        racks[key] = plant.item(key, designation=key.upper(), unit=unit)
        plant.item(f"m_{key}", designation="A1", part=part.id, parent=racks[key], unit=unit)
    plant.item("loose", designation="X1", unit=one)
    model = plant.model()
    assert unit_racks(model, one) == tuple(sorted((racks["r_a"], racks["r_b"])))
    assert unit_racks(model, two) == (racks["r_c"],)
    assert unit_racks(model, None) == tuple(sorted(racks.values()))
