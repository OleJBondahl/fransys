"""Tests for `harness_cables` (design/derive-queries-structure.md, decision 0027)."""

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from connector_builders import make_connector
from plant import Plant
from query_builders import make_core, make_part, make_pin, make_terminal, reversed_tables

from fransys_model.derive import cable_rows, harness_cables, top_level_cables
from fransys_model.kernel import Id, SchemaError, make_id
from fransys_model.vocab.aspects import AspectNode, Placement
from fransys_model.vocab.enums import Aspect, Gender, PartCategory
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet
from fransys_model.vocab.facets.connector import ConnectorFacet
from fransys_model.vocab.facets.terminal import TerminalFacet
from fransys_model.vocab.facets.wire import WireFacet
from fransys_model.vocab.templates import FunctionTemplate

if TYPE_CHECKING:
    from fransys_model.derive import HarnessCable
    from fransys_model.kernel import Model
    from fransys_model.vocab.core import Item, Port


class _Harness:
    """Harness `WH1` with cable `W1` (four cores) between housing `H1` and three sensors."""

    def __init__(self, *, gender_stated: bool = True) -> None:
        self.plant = Plant()
        self.harness = self.plant.item("wh1", designation="WH1")
        self.housing = self.plant.item("h1", parent=self.harness, designation="H1")
        self.p1, self.ports = make_connector(
            self.plant,
            ("h1", "P1"),
            ("1", "2", "10", "A1"),
            gender=Gender.FEMALE if gender_stated else None,
        )
        if not gender_stated:
            # a `connector` facet that states no gender (decision model-0080)
            self.plant.add(
                ConnectorFacet(
                    id=make_id(ConnectorFacet, ("h1", "P1", "connector")),
                    key=("h1", "P1", "connector"),
                    subject=make_id(FunctionTemplate, ("h1", "P1", "template")),
                    style="header",
                    pincount=4,
                )
            )
        self.cable = self.cable_item("w1", "W1", part="cab4", length=1500)
        self.sensors = [make_pin(self.plant, f"b{n}", f"B{n}") for n in (10, 11)]
        self.cores = [
            make_core(
                self.plant, "core-1", self.cable, (self.ports["A1"], self.sensors[0]), index=1
            ),
            make_core(
                self.plant, "core-2", self.cable, (self.ports["2"], self.sensors[1]), index=2
            ),
        ]

    def cable_item(
        self, key: str, designation: str | None, *, part: str, length: int | None
    ) -> Id[Item]:
        """A cable child of the harness with a part, its product facet and a `cable` facet."""
        part_id = make_part(self.plant, part, f"MPN-{part}", category=PartCategory.CABLE)
        self.plant.add(
            CableProductFacet(
                id=make_id(CableProductFacet, (part, "product")),
                key=(part, "product"),
                subject=part_id,
                core_colours=("a", "b", "c", "d"),
                gauge_mm2=Decimal("0.5"),
                shielded=True,
            )
        )
        item = self.plant.item(key, parent=self.harness, part=part_id, designation=designation)
        self.plant.add(
            CableFacet(
                id=make_id(CableFacet, (key, "cable")),
                key=(key, "cable"),
                subject=item,
                length_mm=length,
            )
        )
        return item

    def model(self) -> Model:
        return self.plant.model()


def test_a_cable_carries_its_product_facts_and_its_length() -> None:
    """Part fields, the `cable_product` facet and the item's `cable` facet, as one row."""
    harness = _Harness()
    (cable,) = harness_cables(harness.model(), harness.harness)
    assert (cable.cable, cable.designation) == (harness.cable, "-WH1-W1")
    assert (cable.mpn, cable.description) == ("MPN-cab4", "Invented cab4")
    assert (cable.core_count, cable.gauge_mm2, cable.shielded) == (4, Decimal("0.5"), True)
    assert cable.length_mm == 1500


def test_a_cables_core_count_is_the_length_of_its_products_core_colours() -> None:
    """SC4: the facet stores no count; the row's `core_count` is `len(core_colours)`."""
    plant = Plant()
    harness = plant.item("wh1", designation="WH1")
    part = make_part(plant, "cab2", "MPN-cab2", category=PartCategory.CABLE)
    plant.add(
        CableProductFacet(
            id=make_id(CableProductFacet, ("cab2", "product")),
            key=("cab2", "product"),
            subject=part,
            core_colours=("brown", "blue", "black"),
            gauge_mm2=Decimal("0.5"),
            shielded=False,
        )
    )
    cable = plant.item("w1", parent=harness, part=part, designation="W1")
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w1", "cable")),
            key=("w1", "cable"),
            subject=cable,
            length_mm=None,
        )
    )
    (row,) = harness_cables(plant.model(), harness)
    assert row.core_count == 3


def test_a_cable_facet_with_no_cable_part_is_not_a_cable() -> None:
    """A `CableFacet` item whose part has no `cable_product` facet is not a cable (decision
    model-0108): `harness_cables` finds none of the harness's children to draw."""
    plant = Plant()
    harness = plant.item("wh1", designation="WH1")
    part = make_part(plant, "bare", "MPN-BARE")
    cable = plant.item("w1", parent=harness, part=part, designation="W1")
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w1", "cable")),
            key=("w1", "cable"),
            subject=cable,
            length_mm=None,
        )
    )
    assert harness_cables(plant.model(), harness) == ()


def test_a_cable_facet_with_no_part_at_all_is_not_a_cable() -> None:
    """A `CableFacet` item with no part at all is not a cable (decision model-0108):
    `harness_cables` finds none of the harness's children to draw."""
    plant = Plant()
    harness = plant.item("wh1", designation="WH1")
    cable = plant.item("w1", parent=harness, designation="W1")
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w1", "cable")),
            key=("w1", "cable"),
            subject=cable,
            length_mm=900,
        )
    )
    assert harness_cables(plant.model(), harness) == ()


def test_the_cores_are_the_cable_rows_facts_in_the_same_order() -> None:
    """Shared code: index, colour and both ends, `end_a`/`end_b` included, as `cable_rows` gives
    them -- `cable_rows` itself orients every core to the cable's one direction now (decision
    model-0048), so `harness_cables` has nothing left to reorient and the two agree exactly, not
    just on the unordered pair of ports."""
    harness = _Harness()
    model = harness.model()
    (cable,) = harness_cables(model, harness.harness)
    assert [
        (c.conductor, c.index, c.colour, c.end_a, c.end_a_designation, c.end_b, c.end_b_designation)
        for c in cable.cores
    ] == [
        (r.conductor, r.index, r.colour, r.end_a, r.end_a_designation, r.end_b, r.end_b_designation)
        for r in cable_rows(model, harness.cable)
    ]
    assert [c.index for c in cable.cores] == [1, 2]


def test_a_core_carries_the_label_of_its_wire_facet_or_none() -> None:
    """The label of the conductor's `wire` facet, `None` for a core without one."""
    harness = _Harness()
    harness.plant.add(
        WireFacet(
            id=make_id(WireFacet, ("core-1", "wire")),
            key=("core-1", "wire"),
            subject=harness.cores[0],
            colour="brown",
            gauge_mm2=Decimal("0.5"),
            length_mm=None,
            label="L-1",
        )
    )
    (cable,) = harness_cables(harness.model(), harness.harness)
    assert [(core.index, core.label) for core in cable.cores] == [(1, "L-1"), (2, None)]


def test_an_end_at_a_connector_takes_the_connector_facet_and_only_the_pins_landed_on() -> None:
    """`H1` is a connector end: style, pin count, gender, MPN; pins `A1` and `2` of its four."""
    harness = _Harness()
    (cable,) = harness_cables(harness.model(), harness.harness)
    housing = next(end for end in cable.ends if end.designation == "-WH1-H1")
    assert housing.connector == harness.p1
    assert (housing.style, housing.pincount, housing.gender) == ("header", 4, Gender.FEMALE)
    assert housing.mpn is None
    assert [(pin.marking, pin.port) for pin in housing.pins] == [
        ("2", harness.ports["2"]),
        ("A1", harness.ports["A1"]),
    ]


def test_a_connector_facet_with_no_gender_gives_an_end_whose_gender_is_none() -> None:
    """Decision model-0080: an unstated gender is `None` on the end; style and pin count stay."""
    harness = _Harness(gender_stated=False)
    (cable,) = harness_cables(harness.model(), harness.harness)
    housing = next(end for end in cable.ends if end.designation == "-WH1-H1")
    assert (housing.style, housing.pincount, housing.gender) == ("header", 4, None)


def test_an_end_at_a_plain_device_has_no_connector_fields() -> None:
    """A sensor is an end with `None` connector, style, pin count, gender and MPN."""
    harness = _Harness()
    (cable,) = harness_cables(harness.model(), harness.harness)
    sensor = next(end for end in cable.ends if end.designation == "-B10")
    assert (sensor.connector, sensor.style, sensor.pincount, sensor.gender) == (None,) * 4
    assert sensor.mpn is None
    assert [pin.marking for pin in sensor.pins] == ["1"]


def test_pins_follow_the_digits_first_pin_order_of_connector_rows() -> None:
    """Cores on `A1`, `10`, `2` and `1`: `1, 2, 10, A1`, not the string order."""
    harness = _Harness()
    for name, index, marking in (("core-3", 3, "10"), ("core-4", 4, "1")):
        far = make_pin(harness.plant, name, name.upper())
        make_core(harness.plant, name, harness.cable, (harness.ports[marking], far), index=index)
    (cable,) = harness_cables(harness.model(), harness.harness)
    housing = next(end for end in cable.ends if end.designation == "-WH1-H1")
    assert [pin.marking for pin in housing.pins] == ["1", "2", "10", "A1"]


def test_one_end_per_item_even_when_two_cores_land_on_it() -> None:
    """Cores 1 and 2 both land on `H1`: one end holding both pins."""
    harness = _Harness()
    (cable,) = harness_cables(harness.model(), harness.harness)
    assert sorted(end.designation for end in cable.ends) == ["-B10", "-B11", "-WH1-H1"]


def test_a_connector_function_without_a_facet_is_not_the_ends_connector() -> None:
    """A landing on a connector-kind function with no facet makes a plain device end."""
    plant = Plant()
    harness = plant.item("wh1", designation="WH1")
    plant.item("shell", parent=harness, designation="S1")
    _, shell_ports = make_connector(plant, ("shell", "PE"), ("PE",), gender=None)
    cable = plant.item("w1", parent=harness, designation="W1")
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w1", "cable")), key=("w1", "cable"), subject=cable, length_mm=1
        )
    )
    make_core(plant, "core", cable, (shell_ports["PE"], make_pin(plant, "far", "F1")), index=1)
    (row,) = harness_cables(plant.model(), harness)
    shell = next(end for end in row.ends if end.designation == "-WH1-S1")
    assert (shell.connector, shell.style, shell.pincount, shell.gender) == (None,) * 4
    assert [pin.marking for pin in shell.pins] == ["PE"]


def test_two_connectors_on_one_item_take_the_smallest_function_id_with_a_facet() -> None:
    """Cores land on `P1` and `P2` of one housing: the connector is the smaller function id."""
    plant = Plant()
    harness = plant.item("wh1", designation="WH1")
    plant.item("h1", parent=harness, designation="H1")
    first, first_ports = make_connector(plant, ("h1", "P1"), ("1",))
    second, second_ports = make_connector(plant, ("h1", "P2"), ("1",))
    cable = plant.item("w1", parent=harness, designation="W1")
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w1", "cable")), key=("w1", "cable"), subject=cable, length_mm=1
        )
    )
    make_core(plant, "c1", cable, (first_ports["1"], make_pin(plant, "f1", "F1")), index=1)
    make_core(plant, "c2", cable, (second_ports["1"], make_pin(plant, "f2", "F2")), index=2)
    (row,) = harness_cables(plant.model(), harness)
    housing = next(end for end in row.ends if end.designation == "-WH1-H1")
    assert housing.connector == min(first, second)
    assert len(housing.pins) == 2


def test_only_the_harnesss_children_with_a_cable_facet_are_cables() -> None:
    """A child without the facet, a cable of another harness and a cable child of a child: none."""
    harness = _Harness()
    plant = harness.plant
    plant.item("bare", parent=harness.harness, designation="X1")
    other = plant.item("wh2", designation="WH2")
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w9", "cable")),
            key=("w9", "cable"),
            subject=plant.item("w9", parent=other, designation="W9"),
            length_mm=1,
        )
    )
    rows = harness_cables(harness.model(), harness.harness)
    assert [row.designation for row in rows] == ["-WH1-W1"]


def test_a_harness_with_no_cable_gives_the_empty_tuple() -> None:
    """The housing alone is a harness with nothing to draw."""
    plant = Plant()
    harness = plant.item("wh1", designation="WH1")
    plant.item("h1", parent=harness, designation="H1")
    assert harness_cables(plant.model(), harness) == ()


def test_cables_are_sorted_by_designation_then_id_and_ends_likewise() -> None:
    """`W10` sorts before `W2` as whole strings; the ends of each cable by designation."""
    harness = _Harness()
    for key, designation in (("w10", "W10"), ("w02", "W02")):
        harness.cable_item(key, designation, part="cab4", length=None)
    rows = harness_cables(harness.model(), harness.harness)
    assert [row.designation for row in rows] == ["-WH1-W02", "-WH1-W1", "-WH1-W10"]
    ends = [end.designation for end in rows[1].ends]
    assert ends == sorted(ends)


def test_the_rows_do_not_depend_on_table_order() -> None:
    """The tables backwards, under another digest, give the same rows."""
    harness = _Harness()
    harness.cable_item("w2", "W2", part="cab4", length=10)
    model = harness.model()
    assert harness_cables(reversed_tables(model), harness.harness) == harness_cables(
        model, harness.harness
    )


def test_a_harness_that_is_not_an_item_raises() -> None:
    """The refusal every query gives for an identity id the model does not hold."""
    with pytest.raises(SchemaError):
        harness_cables(Plant().model(), Id(kind="item", value="9" * 32))


def test_a_cable_end_on_two_terminals_of_one_strip_is_one_node() -> None:
    """Two cores land on different terminals of strip `X1`: one end, the strip, not two, pins
    marked by each terminal's own designation (decision model-0046, designer ruling
    2026-09-23 "cable-end-per-strip")."""
    harness = _Harness()
    strip = harness.plant.item("x1", designation="X1")
    l1 = make_terminal(harness.plant, "x1", "t-l1", group="L", index=1)
    l2 = make_terminal(harness.plant, "x1", "t-l2", group="L", index=2)
    far1 = make_pin(harness.plant, "far1", "F1")
    far2 = make_pin(harness.plant, "far2", "F2")
    make_core(harness.plant, "core-a", harness.cable, (l1.external, far1), index=3)
    make_core(harness.plant, "core-b", harness.cable, (l2.external, far2), index=4)
    (cable,) = harness_cables(harness.model(), harness.harness)
    strip_ends = [end for end in cable.ends if end.item == strip]
    assert len(strip_ends) == 1
    (strip_end,) = strip_ends
    assert strip_end.designation == "-X1"
    assert sorted(pin.marking for pin in strip_end.pins) == ["L:1", "L:2"]
    assert (strip_end.connector, strip_end.style, strip_end.pincount, strip_end.gender) == (
        None,
    ) * 4


def test_two_strips_whose_terminals_share_one_designation_are_two_ends() -> None:
    """`X1`'s and `X2`'s `L:1` terminals collide in raw text -- the bug this decision fixes,
    WireViz's dot crash on the two-ends-become-one-node case -- but the strip grouping keeps
    them two distinct ends, titled by their own strips, never merged. Each pin's own `marking`
    still reads the bare `"L:1"` on both (decision model-0052): the end's own `designation`
    already carries the strip, dashed, and every consumer that draws a pin joins the two
    itself, so the marking must not repeat it."""
    plant = Plant()
    x1 = plant.item("x1", designation="X1")
    x2 = plant.item("x2", designation="X2")
    l1 = make_terminal(plant, "x1", "t1", group="L", index=1)
    l2 = make_terminal(plant, "x2", "t2", group="L", index=1)
    cable = plant.item("w1", designation="W1")
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w1", "cable")), key=("w1", "cable"), subject=cable, length_mm=1
        )
    )
    make_core(plant, "core", cable, (l1.external, l2.external), index=1)
    (row,) = top_level_cables(plant.model())
    assert len(row.ends) == 2
    assert {end.item for end in row.ends} == {x1, x2}
    assert {end.designation for end in row.ends} == {"-X1", "-X2"}
    assert all(pin.marking == "L:1" for end in row.ends for pin in end.pins)


def test_a_placed_strips_end_prints_its_product_designation_always() -> None:
    """A strip placed in the location aspect prints the same text the terminal list and every
    other export already print for it, `product_designation`'s own `"+DB-X0"` (decision
    model-0044) -- unconditionally, whatever the cable's other end does (designer ruling
    2026-09-24, model-0046's own amendment: "the rule is the text every other list prints for
    that strip, so a cable drawing never disagrees with the terminal list")."""
    plant = Plant()
    strip = plant.item("x0", designation="X0")
    node = AspectNode(
        id=make_id(AspectNode, ("db",)),
        key=("db",),
        aspect=Aspect.LOCATION,
        parent=None,
        label="DB",
        description="Invented",
    )
    plant.add(node)
    plant.add(
        Placement(id=make_id(Placement, ("p-loc",)), key=("p-loc",), item=strip, node=node.id)
    )
    l1 = make_terminal(plant, "x0", "t1", group="L", index=1)
    far = make_pin(plant, "far", "F1")
    cable = plant.item("w1", designation="W1")
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w1", "cable")), key=("w1", "cable"), subject=cable, length_mm=1
        )
    )
    make_core(plant, "core", cable, (l1.external, far), index=1)
    (row,) = top_level_cables(plant.model())
    strip_end = next(end for end in row.ends if end.item == strip)
    assert strip_end.designation == "+DB-X0"


def test_a_parentless_terminal_keeps_the_per_terminal_end() -> None:
    """A terminal with no strip to group under (`designation.port_designation`'s own defensive
    case) is left as its own end, exactly as before: designation `"L:1"`, pin marked by the raw
    port name."""
    plant = Plant()
    item = plant.item("t1")
    plant.add(
        TerminalFacet(
            id=make_id(TerminalFacet, ("t1", "facet")),
            key=("t1", "facet"),
            subject=item,
            group="L",
            index=1,
        )
    )
    port = plant.port(plant.function(item, "fn"), "1")
    far = make_pin(plant, "far", "F1")
    cable = plant.item("w1", designation="W1")
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w1", "cable")), key=("w1", "cable"), subject=cable, length_mm=1
        )
    )
    make_core(plant, "core", cable, (port, far), index=1)
    (row,) = top_level_cables(plant.model())
    end = next(end for end in row.ends if end.item == item)
    assert end.designation == "-L:1"
    assert [pin.marking for pin in end.pins] == ["1"]


def test_an_unnumbered_cable_or_end_raises() -> None:
    """Designations are rendered, so the cable and every item a core lands on need one."""
    harness = _Harness()
    harness.cable_item("w3", None, part="cab4", length=None)
    with pytest.raises(SchemaError):
        harness_cables(harness.model(), harness.harness)
    plant = Plant()
    wh1 = plant.item("wh1", designation="WH1")
    cable = plant.item("w1", parent=wh1, designation="W1")
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w1", "cable")), key=("w1", "cable"), subject=cable, length_mm=1
        )
    )
    port: Id[Port] = make_pin(plant, "bare", None)
    make_core(plant, "core", cable, (make_pin(plant, "ok", "B1"), port), index=1)
    with pytest.raises(SchemaError):
        harness_cables(plant.model(), wh1)


def test_every_core_of_a_multi_core_cable_runs_the_same_way_round() -> None:
    """Two cores between a strip and two different devices: whichever port a `Conductor` happens
    to hash smaller (`vocab.connectivity.Conductor`'s own "direction is not a fact"), `cable_rows`
    reorients every core to the cable's one direction (decision model-0048, designer ruling
    2026-09-24: "every core runs A->B"). The strip is placed at a location, the two devices are
    not, so `cable_end_rank` puts the strip first for both cores regardless of port-id luck:
    `end_a` is always one of the strip's two terminal ports, never a device port.
    """
    plant = Plant()
    strip = plant.item("x1", designation="X1")
    node = AspectNode(
        id=make_id(AspectNode, ("loc",)),
        key=("loc",),
        aspect=Aspect.LOCATION,
        parent=None,
        label="DB",
        description="Invented",
    )
    plant.add(node)
    plant.add(
        Placement(id=make_id(Placement, ("p-loc",)), key=("p-loc",), item=strip, node=node.id)
    )
    t1 = make_terminal(plant, "x1", "t1", group="L", index=1)
    t2 = make_terminal(plant, "x1", "t2", group="L", index=2)
    d1 = make_pin(plant, "d1", "B1")
    d2 = make_pin(plant, "d2", "B2")
    cable = plant.item("w1", designation="W1")
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w1", "cable")), key=("w1", "cable"), subject=cable, length_mm=1
        )
    )
    make_core(plant, "core-1", cable, (t1.external, d1), index=1)
    make_core(plant, "core-2", cable, (t2.external, d2), index=2)
    model = plant.model()
    (row,) = top_level_cables(model)
    assert {core.end_a for core in row.cores} == {t1.external, t2.external}
    assert {core.end_b for core in row.cores} == {d1, d2}


def test_every_cores_end_ports_are_pins_of_its_own_rows_ends() -> None:
    """Pins the invariant `harness_input`'s own removed guard once asserted (WORK ORDER
    WIREVIZ-CORE-GUARD, designer 2026-09-27, mutmut suspect 2): every `HarnessCore.end_a`/
    `end_b` a row carries is the `port` of one of that same row's own `HarnessEnd.pins`,
    whatever shape the row takes -- a connector end, a plain device, or a terminal strip, one
    end per row or several. `_ends` guarantees this by construction (it builds each end's pins
    from the very cores it is given, decision 0027), so this is the record of that guarantee,
    not a probe of one particular fixture.
    """
    rows: list[HarnessCable] = []

    plain = _Harness()
    rows.extend(harness_cables(plain.model(), plain.harness))

    mixed = _Harness()
    mixed.plant.item("x1", designation="X1")
    l1 = make_terminal(mixed.plant, "x1", "t-l1", group="L", index=1)
    l2 = make_terminal(mixed.plant, "x1", "t-l2", group="L", index=2)
    far1 = make_pin(mixed.plant, "far1", "F1")
    far2 = make_pin(mixed.plant, "far2", "F2")
    make_core(mixed.plant, "core-a", mixed.cable, (l1.external, far1), index=3)
    make_core(mixed.plant, "core-b", mixed.cable, (l2.external, far2), index=4)
    rows.extend(harness_cables(mixed.model(), mixed.harness))

    strips = Plant()
    strips.item("x1", designation="X1")
    strips.item("x2", designation="X2")
    t1 = make_terminal(strips, "x1", "t1", group="L", index=1)
    t2 = make_terminal(strips, "x2", "t2", group="L", index=1)
    strip_cable = strips.item("w1", designation="W1")
    strips.add(
        CableFacet(
            id=make_id(CableFacet, ("w1", "cable")),
            key=("w1", "cable"),
            subject=strip_cable,
            length_mm=1,
        )
    )
    make_core(strips, "core", strip_cable, (t1.external, t2.external), index=1)
    rows.extend(top_level_cables(strips.model()))

    assert rows, "the invariant is vacuous if nothing here builds a row"
    for cable in rows:
        landed = {pin.port for end in cable.ends for pin in end.pins}
        for core in cable.cores:
            assert core.end_a in landed
            assert core.end_b in landed
