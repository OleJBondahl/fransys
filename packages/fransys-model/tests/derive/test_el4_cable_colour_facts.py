"""EL-4 facts: `cables` (product, counts, gaps), `colours` (reads) and `potentials` (wired)."""

from decimal import Decimal

from plant import Plant
from query_builders import make_part, make_pin

from fransys_model.derive.facts.cables import (
    cable_product,
    core_count_gaps,
    core_counts,
    wired_cores_past_product,
)
from fransys_model.derive.facts.colours import (
    coloured_conductors,
    unknown_core_colours,
    unknown_wire_colours,
)
from fransys_model.derive.facts.potentials import is_wired, on_declared_net, pe_ports_off_pe
from fransys_model.kernel import Id, make_id
from fransys_model.vocab.core import Item, Port
from fransys_model.vocab.enums import PartCategory, PortRole
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet, CoreFacet
from fransys_model.vocab.facets.wire import WireFacet
lazy from fransys_model.vocab.connectivity import Conductor


def _plant(colours: tuple[str, ...]) -> Plant:
    """A cable `w1` whose product lists `colours`."""
    plant = Plant()
    part = make_part(plant, "cab", "MPN-cab", category=PartCategory.CABLE)
    key = ("cab", "product")
    plant.add(
        CableProductFacet(
            id=make_id(CableProductFacet, key),
            key=key,
            subject=part,
            core_colours=colours,
            gauge_mm2=Decimal("0.5"),
            shielded=False,
        )
    )
    cable = plant.item("w1", designation="W1", part=part)
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w1", "c")), key=("w1", "c"), subject=cable, length_mm=None
        )
    )
    return plant


def _core(plant: Plant, index: int) -> Id[Conductor]:
    key = f"c{index}"
    core = plant.core(
        make_pin(plant, f"a{key}", f"A{index}"),
        make_pin(plant, f"b{key}", f"B{index}"),
        key=key,
        carrier=make_id(Item, ("w1",)),
    )
    facet = CoreFacet(id=make_id(CoreFacet, (key, "f")), key=(key, "f"), subject=core, index=index)
    plant.add(facet)
    return core


def test_cable_product_is_the_product_of_the_items_part() -> None:
    # MUTATION: `cable_product` keys the product by item, not by part
    model = _plant(("BN",)).model()
    assert cable_product(model, make_id(Item, ("w1",))) is not None
    assert cable_product(model, make_id(Item, ("nobody",))) is None


def test_core_counts_and_gaps_and_past_product() -> None:
    # MUTATION: `cores_past_product` accepts index == count + 1, or `core_counts` skips cores
    plant = _plant(("BN", "BU"))
    _core(plant, 1)
    past = _core(plant, 3)
    model = plant.model()
    cable = make_id(Item, ("w1",))
    assert core_counts(model)[cable] == 2
    assert wired_cores_past_product(model) == ((cable, past, 3, 2),)
    assert core_count_gaps(model) == ()


def test_a_core_takes_its_products_colour_and_none_past_it() -> None:
    # MUTATION: `_core_colours` indexes from 0
    plant = _plant(("BN", "BU"))
    first, past = _core(plant, 1), _core(plant, 3)
    model = plant.model()
    assert past not in {c for c, _, _ in coloured_conductors(model)}
    assert coloured_conductors(model) == ((first, "BN", None),)


def test_unknown_colours_are_listed_for_wires_and_products() -> None:
    # MUTATION: `unknown_wire_colours` flags the legal empty colour
    plant = _plant(("BN", "ZZ"))
    for key, colour in (("ok", ""), ("bad", "QQ")):
        wire = plant.wire(make_pin(plant, f"{key}a", "A"), make_pin(plant, f"{key}b", "B"), key=key)
        plant.add(
            WireFacet(
                id=make_id(WireFacet, (key, "f")),
                key=(key, "f"),
                subject=wire,
                colour=colour,
                gauge_mm2=Decimal("0.5"),
                length_mm=None,
                label=None,
            )
        )
    model = plant.model()
    assert [f.colour for f in unknown_wire_colours(model)] == ["QQ"]
    assert [(i, c) for _, i, c in unknown_core_colours(model)] == [(2, "ZZ")]


def test_is_wired_and_pe_ports_off_pe() -> None:
    # MUTATION: `is_wired` is true for a lone port
    plant = Plant()
    function = plant.function(plant.item("m1"), "motor")
    key = ("m1", "motor", "PE")
    pe = Port(
        id=make_id(Port, key),
        key=key,
        function=function,
        template=None,
        name="PE",
        role=PortRole.PE,
    )
    plant.add(pe)
    assert not is_wired(plant.model(), pe.id)
    assert pe_ports_off_pe(plant.model()) == ()
    plant.wire(pe.id, make_pin(plant, "loose", "L"), key="w")
    model = plant.model()
    assert is_wired(model, pe.id)
    assert pe_ports_off_pe(model) == (pe.id,)
    assert not on_declared_net(model, pe.id)


def test_on_declared_net_is_false_for_an_unknown_port() -> None:
    port: Id[Port] = make_id(Port, ("nowhere",))
    assert not on_declared_net(Plant().model(), port)


def test_cores_past_product_is_one_rule_on_plain_values() -> None:
    # MUTATION: the range is 0-based or one core too wide
    from fransys_model.derive import cores_past_product

    assert [cores_past_product(2, n) for n in (0, 1, 2, 3)] == [True, False, False, True]
