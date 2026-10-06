"""Cable ends are product designations and cable tags carry their sign (designer ruling 2026-09-24).

Every `HarnessEnd.designation` is `product_designation` (a strip, a plug and a plain device alike);
`cable_list_rows`' `from_label`/`to_label` are those very values; a cable's own tag reads `"-W1"`
in `HarnessCable`, `CableListRow` and `CableRow`.
"""

from decimal import Decimal

from plant import Plant
from query_builders import make_core, make_node, make_placement, make_terminal

from fransys_model.derive import cable_list_rows, cable_rows, top_level_cables
from fransys_model.kernel import make_id
from fransys_model.vocab.enums import PartCategory
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet
from fransys_model.vocab.templates import Part


def _model_with_strip_and_motor_ends():
    """`W1` and `W2` run from strip `X1` (placed at `C1`) to motors `M1`, `M2` placed at `EXT`."""
    plant = Plant()
    c1, ext = make_node("c1", None), make_node("ext", None)
    plant.add(c1, ext)
    strip = plant.item("x1", designation="X1")
    plant.add(make_placement("x1-loc", strip, c1.id))
    for n in (1, 2):
        terminal = make_terminal(plant, "x1", f"t{n}", group="L", index=n)
        motor = plant.item(f"m{n}", designation=f"M{n}")
        motor_port = plant.port(plant.function(motor, "f"), "1")
        plant.add(make_placement(f"m{n}-loc", motor, ext.id))
        # A cable part (RW4b: `is_cable` needs a `CableProductFacet`, not just a `cable`
        # facet); `core_colours` starts empty and `make_core`'s `_colour_core` grows it to
        # match the one core added below.
        part = Part(
            id=make_id(Part, (f"w{n}", "cable-part")),
            key=(f"w{n}", "cable-part"),
            mpn=f"MPN-w{n}",
            manufacturer="Example Co",
            description=f"Invented w{n}",
            category=PartCategory.CABLE,
            class_code="",
        )
        plant.add(
            part,
            CableProductFacet(
                id=make_id(CableProductFacet, (f"w{n}", "product")),
                key=(f"w{n}", "product"),
                subject=part.id,
                core_colours=(),
                gauge_mm2=Decimal("0.5"),
                shielded=False,
            ),
        )
        cable = plant.item(f"w{n}", designation=f"W{n}", part=part.id)
        plant.add(
            CableFacet(
                id=make_id(CableFacet, (f"w{n}", "cable")),
                key=(f"w{n}", "cable"),
                subject=cable,
                length_mm=None,
            )
        )
        make_core(plant, f"core-{n}", cable, (terminal.external, motor_port), index=1)
    return plant.model()


def test_cable_list_labels_are_the_two_lowest_ranked_ends_designations() -> None:
    """Both queries, compared: the row's text is the drawing's text, never built a second time."""
    model = _model_with_strip_and_motor_ends()
    rows = {row.cable: row for row in cable_list_rows(model)}
    cables = top_level_cables(model)
    assert len(cables) == len(rows) == 2
    for cable in cables:
        assert len(cable.ends) == 2
        row = rows[cable.cable]
        assert (row.from_label, row.to_label) == tuple(end.designation for end in cable.ends[:2])


def test_a_motor_end_reads_its_location_and_tag_in_the_end_and_the_row() -> None:
    """A motor placed at `EXT` is `+EXT-M1` in the end's designation and in from/to (not `M1`)."""
    model = _model_with_strip_and_motor_ends()
    cable = next(c for c in top_level_cables(model) if c.designation == "-W1")
    (row,) = (r for r in cable_list_rows(model) if r.designation == "-W1")
    assert [end.designation for end in cable.ends] == ["+C1-X1", "+EXT-M1"]
    assert (row.from_label, row.to_label) == ("+C1-X1", "+EXT-M1")


def test_every_cable_tag_carries_its_sign() -> None:
    """`HarnessCable`, `CableListRow` and `CableRow` all print `-W1`, never the bare `W1`."""
    model = _model_with_strip_and_motor_ends()
    cable = next(c for c in top_level_cables(model) if c.designation.endswith("W1"))
    assert cable.designation == "-W1"
    assert {row.designation for row in cable_list_rows(model)} == {"-W1", "-W2"}
    assert {row.cable_designation for row in cable_rows(model, cable.cable)} == {"-W1"}
