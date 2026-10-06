"""A unit's cable end reads the EFFECTIVE location placement, as its lists do (Q7, model-0090).

A device `D1` with no placement of its own sits in a housing `H1` placed at `+EXT`; the top-level
board unit `bu` has its root `A1` at `+C1`. In `bu`'s document `D1` prints `+EXT-D1`, the same text
`port_designation_in` gives for its port in the unit's lists; read absolute (`unit=None`) it keeps
its OWN placement, none, and prints as `product_designation` does. Invented data.
"""

from decimal import Decimal

from plant import Plant
from query_builders import make_core, make_node, make_placement

from fransys_model.derive import unit_cables
from fransys_model.derive.designation import product_designation, unit_list_context
from fransys_model.derive.drawing_text import port_designation_in, product_designation_in
from fransys_model.kernel import make_id
from fransys_model.vocab.enums import PartCategory
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet
from fransys_model.vocab.templates import Part


def _scene():
    plant = Plant()
    c1, ext = make_node("c1", None), make_node("ext", None)
    plant.add(c1, ext)
    bu = plant.unit("bu", name="bu")
    board = plant.item("a1", designation="A1", part=plant.board_part(), unit=bu)
    k1 = plant.item("k1", designation="K1", parent=board, unit=bu)
    housing = plant.item("h1", designation="H1")
    device = plant.item("d1", designation="D1", parent=housing)
    plant.add(make_placement("a1-loc", board, c1.id), make_placement("h1-loc", housing, ext.id))
    cable_part = Part(
        id=make_id(Part, ("w1", "part")),
        key=("w1", "part"),
        mpn="MPN-w1",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.CABLE,
        class_code="W",
    )
    cable_product = CableProductFacet(
        id=make_id(CableProductFacet, ("w1", "part", "product")),
        key=("w1", "part", "product"),
        subject=cable_part.id,
        core_colours=(),
        gauge_mm2=Decimal("0.5"),
        shielded=False,
    )
    plant.add(cable_part, cable_product)
    cable = plant.item("w1", designation="W1", parent=board, unit=bu, part=cable_part.id)
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w1", "cable")),
            key=("w1", "cable"),
            subject=cable,
            length_mm=None,
        )
    )
    k1_pin = plant.port(plant.function(k1, "f"), "1")
    d1_pin = plant.port(plant.function(device, "f"), "1")
    make_core(plant, "core", cable, (k1_pin, d1_pin), index=1)
    return plant.model(), bu, device, d1_pin


def test_a_unit_cable_end_with_an_inherited_placement_prints_its_ancestors_path() -> None:
    """`D1` inherits `+EXT` from `H1`: `+EXT-D1` in `bu`'s drawing, the text its list prints."""
    model, bu, device, d1_pin = _scene()
    (cable,) = unit_cables(model, bu)
    (end,) = [end for end in cable.ends if end.item == device]
    assert end.designation == "+EXT-D1"
    context = unit_list_context(model, bu, None)
    assert port_designation_in(model, d1_pin, context, unit=bu) == "+EXT-D1:1"
    assert end.designation == port_designation_in(model, d1_pin, context, unit=bu).removesuffix(
        ":1"
    )


def test_read_absolute_the_same_item_keeps_its_own_placement() -> None:
    """`unit=None`: `D1` has no placement of its own, so no path, as the item document has it."""
    model, _bu, device, _pin = _scene()
    assert product_designation_in(model, device, None) == product_designation(model, device)
    assert product_designation_in(model, device, None) == "-D1"
