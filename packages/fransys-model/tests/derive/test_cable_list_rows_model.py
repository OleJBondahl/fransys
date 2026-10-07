"""Tests for `cable_list_rows` (design/derive-queries-structure.md, units spec U3)."""

from decimal import Decimal

from plant import Plant
from query_builders import make_core, make_node, make_pin, make_placement

from fransys_model.derive import cable_list_rows
from fransys_model.kernel import Id, make_id
from fransys_model.vocab.core import Item, Unit
from fransys_model.vocab.enums import Aspect, PartCategory
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet
from fransys_model.vocab.templates import Part

# Baseline top-level cable count for the exclusion test, asserted before the unit-owned cable
# is added (a named constant, not a bare "at least" count).
BASELINE_CABLE_COUNT = 2


def _item_id(key: str) -> Id[Item]:
    """The id `Plant.item`/`make_pin` gives an item keyed `key`, without building one."""
    return make_id(Item, (key,))


def _cable(plant: Plant, key: str, designation: str, *, unit: Id[Unit] | None = None) -> Id[Item]:
    """A cable item with a `cable` facet and a cable part (RW4b: `is_cable` needs a
    `CableProductFacet`, not just a `cable` facet), `unit` set or left `None`.

    `core_colours` starts empty; `query_builders.make_core`'s `_colour_core` grows it to match
    whatever cores the caller adds afterwards, so it always matches the modelled cores exactly.
    """
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
    item = plant.item(key, designation=designation, unit=unit, part=part.id)
    plant.add(
        CableFacet(
            id=make_id(CableFacet, (key, "cable")),
            key=(key, "cable"),
            subject=item,
            length_mm=None,
        )
    )
    return item


def test_two_unlocated_ends_order_by_product_designation() -> None:
    """`from_label`/`to_label` follow the product-designation tie-break, not the `Item` id.

    Neither end has a `LOCATION` placement, so `cable_end_rank` (decision model-0048) falls
    straight to `product_designation` (designer ruling 2026-09-24, moved from the old smaller-id
    rule).
    The keys are sorted by `Item` id first, then handed designations in *reverse* alphabetical
    order ("K2" to the smaller-id item, "K1" to the larger), so a correct assertion of literal
    values can only pass if the query really orders by designation, never by id.
    """
    plant = Plant()
    cable = _cable(plant, "w1", "W1")
    smaller_key, larger_key = sorted(("e1", "e2"), key=_item_id)
    smaller_end = make_pin(plant, smaller_key, "K2")
    larger_end = make_pin(plant, larger_key, "K1")
    make_core(plant, "core-1", cable, (smaller_end, larger_end), index=1)
    rows = cable_list_rows(plant.model())
    assert len(rows) == 1
    (row,) = rows
    assert (row.cable, row.designation) == (cable, "-W1")
    assert (row.from_label, row.to_label) == ("-K1", "-K2")


def test_an_end_belonging_to_a_unit_is_labelled_by_its_product_designation() -> None:
    """An end whose item belongs to a unit is labelled by its product designation, not the unit."""
    plant = Plant()
    unit = plant.unit("board", name="relay-board", revision=1)
    plant.revision(unit)
    cable = _cable(plant, "w1", "W1")
    loose = make_pin(plant, "loose", "B1")
    boxed_item = plant.item("boxed", designation="X1", unit=unit)
    boxed = plant.port(plant.function(boxed_item, "f"), "1")
    node = make_node("c1", None, Aspect.LOCATION)
    plant.add(node, make_placement("boxed-loc", boxed_item, node.id))
    make_core(plant, "core-1", cable, (loose, boxed), index=1)
    (row,) = cable_list_rows(plant.model())
    labels = {row.from_label, row.to_label}
    assert labels == {"-B1", "+C1-X1"}


def test_a_cable_belonging_to_a_unit_is_excluded() -> None:
    """A unit-owned cable never shows up in `cable_list_rows`; the loose count stays put."""
    plant = Plant()
    _cable(plant, "w1", "W1")
    _cable(plant, "w2", "W2")
    baseline = cable_list_rows(plant.model())
    assert len(baseline) == BASELINE_CABLE_COUNT
    unit = plant.unit("cab", name="pump-cabinet", revision=1)
    plant.revision(unit)
    _cable(plant, "w3", "W3", unit=unit)
    rows = cable_list_rows(plant.model())
    assert len(rows) == BASELINE_CABLE_COUNT
    # examined: the unit-owned cable is really absent, not merely uncounted
    assert "-W3" not in {row.designation for row in rows}


def test_three_ends_list_every_other_end_in_rank_order() -> None:
    """A cable with three unlocated ends: the lowest product-designation end is `from_label`,
    `to_label` lists the others in rank order, joined by ", " (model-0048, model-0155).

    Same construction as the two-end test above: keys sorted by `Item` id, then handed
    designations in reverse alphabetical order ("X3" to the smallest-id item, "X1" to the
    largest), so the literal assertion below can only pass on a true designation sort, not id.
    """
    plant = Plant()
    cable = _cable(plant, "w1", "W1")
    keys = sorted(("e1", "e2", "e3"), key=_item_id)
    designations = dict(zip(keys, ("X3", "X2", "X1"), strict=True))
    ends = {key: make_pin(plant, key, designations[key]) for key in keys}
    make_core(plant, "core-1", cable, (ends[keys[0]], ends[keys[1]]), index=1)
    make_core(plant, "core-2", cable, (ends[keys[1]], ends[keys[2]]), index=2)
    make_core(plant, "core-3", cable, (ends[keys[2]], ends[keys[0]]), index=3)
    (row,) = cable_list_rows(plant.model())
    assert (row.from_label, row.to_label) == ("-X1", "-X2, -X3")


def test_zero_ends_gives_empty_from_and_to_labels() -> None:
    """A cable with no cores at all: both `from_label` and `to_label` are `""`."""
    plant = Plant()
    _cable(plant, "w1", "W1")
    (row,) = cable_list_rows(plant.model())
    assert (row.from_label, row.to_label) == ("", "")


def test_one_end_leaves_to_label_empty() -> None:
    """A cable whose only core lands twice on the same item: one end, `to_label` is `""`."""
    plant = Plant()
    cable = _cable(plant, "w1", "W1")
    item = plant.item("h1", designation="H1")
    fn = plant.function(item, "f")
    a = plant.port(fn, "1")
    b = plant.port(fn, "2")
    make_core(plant, "core-1", cable, (a, b), index=1)
    (row,) = cable_list_rows(plant.model())
    assert row.from_label == "-H1"
    assert row.to_label == ""


def test_a_cable_inside_a_harness_is_still_a_top_level_cable() -> None:
    """A cable child of a harness (itself `unit=None`) is included, same as a loose cable."""
    plant = Plant()
    harness = plant.item("wh1", designation="WH1")
    part = Part(
        id=make_id(Part, ("w1", "cable-part")),
        key=("w1", "cable-part"),
        mpn="MPN-w1",
        manufacturer="Example Co",
        description="Invented w1",
        category=PartCategory.CABLE,
        class_code="",
    )
    plant.add(
        part,
        CableProductFacet(
            id=make_id(CableProductFacet, ("w1", "product")),
            key=("w1", "product"),
            subject=part.id,
            core_colours=(),
            gauge_mm2=Decimal("0.5"),
            shielded=False,
        ),
    )
    cable = plant.item("w1", parent=harness, designation="WH1-W1", part=part.id)
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w1", "cable")),
            key=("w1", "cable"),
            subject=cable,
            length_mm=None,
        )
    )
    rows = cable_list_rows(plant.model())
    assert len(rows) == 1
    assert rows[0].cable == cable


def test_two_cables_between_the_same_two_locations_read_the_same_way_round() -> None:
    """`W11` (a motor to a cabinet strip) and `W21` (another motor to another cabinet strip), the
    same two locations each time: both read motor-first (decision model-0048, designer ruling
    2026-09-24) -- the end order is a property of the two *locations*, `"aa-motor"` sorting
    before `"zz-cabinet"`, never of which end happened to hash the smaller `Item` id.

    `W11`'s keys are handed out so the motor gets the smaller id, `W21`'s so the *strip* gets the
    smaller id -- the old smaller-id rule would have picked the motor for `W11` (by coincidence)
    and the strip for `W21`, disagreeing with itself exactly as the real bug did (`"M1 -> +C1-X3"`
    against `"+C1-X3 -> M2"`). A correct assertion of literal values can only pass if the query
    really orders by location, never by id.
    """
    plant = Plant()
    motor_loc = make_node("aa-motor", None)
    cabinet_loc = make_node("zz-cabinet", None)
    plant.add(motor_loc, cabinet_loc)

    motor_key_11, strip_key_11 = sorted(("e1", "e2"), key=_item_id)
    m1 = plant.item(motor_key_11, designation="M1")
    x3 = plant.item(strip_key_11, designation="X3")
    plant.add(
        make_placement("m1-loc", m1, motor_loc.id), make_placement("x3-loc", x3, cabinet_loc.id)
    )
    m1_port = plant.port(plant.function(m1, "f"), "1")
    x3_port = plant.port(plant.function(x3, "f"), "1")
    w11 = _cable(plant, "w11", "W11")
    make_core(plant, "core-w11", w11, (m1_port, x3_port), index=1)

    strip_key_21, motor_key_21 = sorted(("e3", "e4"), key=_item_id)
    x4 = plant.item(strip_key_21, designation="X4")
    m2 = plant.item(motor_key_21, designation="M2")
    plant.add(
        make_placement("m2-loc", m2, motor_loc.id), make_placement("x4-loc", x4, cabinet_loc.id)
    )
    m2_port = plant.port(plant.function(m2, "f"), "1")
    x4_port = plant.port(plant.function(x4, "f"), "1")
    w21 = _cable(plant, "w21", "W21")
    make_core(plant, "core-w21", w21, (x4_port, m2_port), index=1)

    rows = {row.designation: row for row in cable_list_rows(plant.model())}
    assert rows["-W11"].from_label == "+AA-MOTOR-M1"
    assert rows["-W11"].to_label == "+ZZ-CABINET-X3"
    assert rows["-W21"].from_label == "+AA-MOTOR-M2"
    assert rows["-W21"].to_label == "+ZZ-CABINET-X4"
