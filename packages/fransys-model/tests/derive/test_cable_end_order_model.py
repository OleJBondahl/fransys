"""Cross-query tests for decision model-0048: `cable_rows`, `harness_cables`, and
`cable_list_rows` all share one end order per cable
(`designation.cable_end_rank`/`lookups.cable_end_owner`).
"""

from decimal import Decimal
from typing import Any

from plant import Plant
from query_builders import make_core, make_node, make_placement

from fransys_model.derive import cable_list_rows, cable_rows, wire_rows
from fransys_model.kernel import Id, make_id
from fransys_model.vocab.core import Port
from fransys_model.vocab.enums import PartCategory
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet
from fransys_model.vocab.facets.wire import WireFacet
from fransys_model.vocab.templates import Part


def _cable_part(plant: Plant, key: str) -> Id[Any]:
    """A cable part for `key` (RW4b: `is_cable` needs a `CableProductFacet`, not just a
    `cable` facet); `core_colours` starts empty and `make_core`'s `_colour_core` grows it to
    match the one core each caller here adds afterwards."""
    part = Part(
        id=make_id(Part, (key, "cable-part")),
        key=(key, "cable-part"),
        mpn=f"MPN-{key}",
        manufacturer="Example Co",
        description=f"Invented {key}",
        category=PartCategory.CABLE,
        class_code="",
    )
    plant.add(
        part,
        CableProductFacet(
            id=make_id(CableProductFacet, (key, "product")),
            key=(key, "product"),
            subject=part.id,
            core_colours=(),
            gauge_mm2=Decimal("0.5"),
            shielded=False,
        ),
    )
    return part.id


def _port_id(key: str) -> Id[Port]:
    """The id `Plant.port(Plant.function(item, "f"), "1")` gives for an item keyed `key`."""
    return make_id(Port, (key, "f", "1"))


def test_cable_rows_and_cable_list_rows_read_a_w11_shaped_cable_the_same_way_round() -> None:
    """A `W11`-shaped cable, motor `M1` to cabinet strip `X3`, both located: `cable_rows`' one
    core and `cable_list_rows`' `from_label`/`to_label` name the SAME end first -- the motor,
    whose location `"aa-motor"` sorts before the strip's `"zz-cabinet"` (decision model-0048,
    `designation.cable_end_rank` shared by both queries).

    The strip's item key is chosen to give it the *smaller* port id (`_port_id`, the same
    sorted-key idiom `test_cable_list_rows_model.py` uses): a `Conductor` stores its ends in
    port-id order, so without the reorientation `cable_rows` would read `end_a` = the strip, not
    the motor. Only a real fix, not port-id luck, can make this pass.
    """
    plant = Plant()
    motor_loc = make_node("aa-motor", None)
    cabinet_loc = make_node("zz-cabinet", None)
    plant.add(motor_loc, cabinet_loc)

    motor_key, strip_key = sorted(("e1", "e2"), key=_port_id, reverse=True)
    m1 = plant.item(motor_key, designation="M1")
    x3 = plant.item(strip_key, designation="X3")
    plant.add(
        make_placement("m1-loc", m1, motor_loc.id), make_placement("x3-loc", x3, cabinet_loc.id)
    )
    m1_port = plant.port(plant.function(m1, "f"), "1")
    x3_port = plant.port(plant.function(x3, "f"), "1")
    assert x3_port < m1_port  # the strip's port hashes smaller: the raw, unoriented `a` end
    cable = plant.item("w11", designation="W11", part=_cable_part(plant, "w11"))
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w11", "cable")),
            key=("w11", "cable"),
            subject=cable,
            length_mm=None,
        )
    )
    core = make_core(plant, "core-1", cable, (x3_port, m1_port), index=1)
    plant.add(
        WireFacet(
            id=make_id(WireFacet, ("core-1", "wire")),
            key=("core-1", "wire"),
            subject=core,
            colour="black",
            gauge_mm2=Decimal("0.75"),
            length_mm=None,
            label="L1",
        )
    )
    model = plant.model()

    (csv_row,) = cable_rows(model, cable)
    (list_row,) = cable_list_rows(model)
    assert csv_row.end_a == m1_port
    assert csv_row.end_a_designation.startswith("-M1")
    assert list_row.from_label == "+AA-MOTOR-M1"
    assert list_row.to_label == "+ZZ-CABINET-X3"


def test_wire_rows_has_no_row_for_a_cable_core_that_cable_rows_lists() -> None:
    """A `wire`-faceted `CORE` conductor is a `cable_rows` row only: the wire list holds WIRE kind.

    The strip's port is given the smaller id (`_port_id`), as in the orientation tests above.
    """
    plant = Plant()
    motor_loc = make_node("aa-motor", None)
    cabinet_loc = make_node("zz-cabinet", None)
    plant.add(motor_loc, cabinet_loc)

    motor_key, strip_key = sorted(("e1", "e2"), key=_port_id, reverse=True)
    m1 = plant.item(motor_key, designation="M1")
    x3 = plant.item(strip_key, designation="X3")
    plant.add(
        make_placement("m1-loc", m1, motor_loc.id), make_placement("x3-loc", x3, cabinet_loc.id)
    )
    m1_port = plant.port(plant.function(m1, "f"), "1")
    x3_port = plant.port(plant.function(x3, "f"), "1")
    assert x3_port < m1_port  # the strip's port hashes smaller: the raw, unoriented `a` end
    cable = plant.item("w11", designation="W11", part=_cable_part(plant, "w11"))
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w11", "cable")),
            key=("w11", "cable"),
            subject=cable,
            length_mm=None,
        )
    )
    core = make_core(plant, "core-1", cable, (x3_port, m1_port), index=1)
    plant.add(
        WireFacet(
            id=make_id(WireFacet, ("core-1", "wire")),
            key=("core-1", "wire"),
            subject=core,
            colour="black",
            gauge_mm2=Decimal("0.75"),
            length_mm=None,
            label="L1",
        )
    )
    model = plant.model()

    (csv_row,) = cable_rows(model, cable)
    assert csv_row.conductor == core
    assert wire_rows(model) == ()
