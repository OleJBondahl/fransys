"""V8: `wire_rows`, the wire list's rows: one per wire-faceted `WIRE` conductor, nothing else."""

from decimal import Decimal

from plant import Plant
from query_builders import make_core, make_labelled, make_pin

from fransys_model.derive import WIRE_COLUMNS, column_values, wire_rows
from fransys_model.derive.designation import port_designation
from fransys_model.kernel import make_id
from fransys_model.vocab.enums import ConductorKind
from fransys_model.vocab.facets.wire import WireFacet


def _faceted(plant: Plant, key: str, a, b, kind: ConductorKind):
    """A conductor of `kind` between `a` and `b` that carries a `wire` facet."""
    conductor = plant.wire(a, b, key=key, kind=kind)
    plant.add(
        WireFacet(
            id=make_id(WireFacet, (key, "facet")),
            key=(key, "facet"),
            subject=conductor,
            colour="BU",
            gauge_mm2=Decimal("1.5"),
            length_mm=None,
            label=None,
        )
    )
    return conductor


def test_a_wire_row_carries_ends_colour_cross_section_and_the_printed_label() -> None:
    """The columns are `from`, `to`, `colour`, `cross_section_mm2`, `label`; label is both ends."""
    plant = Plant()
    a, b = make_pin(plant, "i1", "B12"), make_pin(plant, "i2", "Q11")
    wire = make_labelled(plant, "w1", a, b, None)
    model = plant.model()
    (row,) = wire_rows(model)
    assert row.conductor == wire
    assert WIRE_COLUMNS == ("from_", "to", "colour", "cross_section_mm2", "label")
    ends = {port_designation(model, a), port_designation(model, b)}
    assert {row.from_, row.to} == ends
    assert row.label == f"{row.from_} {row.to}"
    assert column_values(row, WIRE_COLUMNS)[2:4] == ("black", Decimal("0.75"))


def test_a_jumper_a_cable_core_and_a_bare_conductor_give_no_wire_row() -> None:
    """One row per wire-faceted `WIRE` conductor and nothing else (V8)."""
    plant = Plant()
    ports = [make_pin(plant, f"i{n}", f"K{n}") for n in range(1, 8)]
    kept = make_labelled(plant, "kept", ports[0], ports[1], None)
    _faceted(plant, "jumper", ports[1], ports[2], ConductorKind.JUMPER)
    plant.wire(ports[2], ports[3], key="bare")
    cable = plant.item("w1", designation="W1")
    make_core(plant, "core", cable, (ports[4], ports[5]), index=1)
    _faceted(plant, "faceted-core", ports[5], ports[6], ConductorKind.CORE)
    assert [row.conductor for row in wire_rows(plant.model())] == [kept]
