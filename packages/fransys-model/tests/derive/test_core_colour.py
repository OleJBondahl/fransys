"""`derive.core_colour`: a core's colour is its carrier's product's `core_colours[index - 1]`."""

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from plant import Plant
from query_builders import make_part, make_pin

from fransys_model.derive import cable_rows, core_colour, harness_cables
from fransys_model.kernel import Id, Model, SchemaError, make_id
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.enums import ConductorKind, PartCategory
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet, CoreFacet
from fransys_model.vocab.facets.wire import WireFacet

if TYPE_CHECKING:
    from fransys_model.vocab.core import Item

_COLOURS = ("BN", "BU", "GN")


def _plant(colours: tuple[str, ...] | None = _COLOURS) -> tuple[Plant, Id[Item], Id[Item]]:
    """A harness `WH1` and its cable `W1` with a `cable` facet, whose part has `colours` as
    `core_colours`; `None` gives a cable with no part."""
    plant = Plant()
    harness = plant.item("wh1", designation="WH1")
    part = None
    if colours is not None:
        part = make_part(plant, "cab", "MPN-cab", category=PartCategory.CABLE)
        plant.add(
            CableProductFacet(
                id=make_id(CableProductFacet, ("cab", "product")),
                key=("cab", "product"),
                subject=part,
                core_colours=colours,
                gauge_mm2=Decimal("0.5"),
                shielded=False,
            )
        )
    cable = plant.item("w1", designation="W1", parent=harness, part=part)
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w1", "cable")),
            key=("w1", "cable"),
            subject=cable,
            length_mm=None,
        )
    )
    return plant, harness, cable


def _core(plant: Plant, cable: Id[Item], index: int | None) -> Id[Conductor]:
    """A core of `cable` with a `core` facet at `index`, or none when `index` is `None`."""
    key = f"core-{index}"
    conductor = plant.core(
        make_pin(plant, f"a-{key}", f"A{index}"),
        make_pin(plant, f"b-{key}", f"B{index}"),
        key=key,
        carrier=cable,
    )
    if index is not None:
        plant.add(
            CoreFacet(
                id=make_id(CoreFacet, (key, "facet")),
                key=(key, "facet"),
                subject=conductor,
                index=index,
            )
        )
    return conductor


@pytest.mark.parametrize(("index", "colour"), [(1, "BN"), (2, "BU"), (3, "GN")])
def test_a_core_has_its_products_colour_at_its_index(index: int, colour: str) -> None:
    # MUTATION: `_colour_at` returns `colours[index]` (first colour missed, last one raises)
    plant, _, cable = _plant()
    core = _core(plant, cable, index)
    assert core_colour(plant.model(), core) == colour


@pytest.mark.parametrize("index", [0, 4, -1])
def test_an_index_outside_the_product_raises(index: int) -> None:
    # MUTATION: `_colour_at` tests `0 <= index` (0 gives `colours[-1]`), `index <= len(colours) + 1`
    # (4 raises IndexError, not SchemaError), or drops the check (-1 gives `colours[-2]`)
    plant, _, cable = _plant()
    core = _core(plant, cable, index)
    with pytest.raises(SchemaError, match="outside its cable product"):
        core_colour(plant.model(), core)


def test_a_wire_has_no_core_colour() -> None:
    # MUTATION: `core_colour` drops the `record.kind is not CORE or record.carrier is None` check
    plant, _, cable = _plant()
    wire = plant.wire(make_pin(plant, "a", "A1"), make_pin(plant, "b", "B1"), key="wire")
    with pytest.raises(SchemaError, match="not a cable core"):
        core_colour(plant.model(), wire)
    # a wire naming the cable as carrier is still no core: only the kind can tell
    plant.add(
        Conductor(
            id=make_id(Conductor, ("carried",)),
            key=("carried",),
            a=make_pin(plant, "c", "C1"),
            b=make_pin(plant, "d", "D1"),
            kind=ConductorKind.WIRE,
            carrier=cable,
        )
    )
    with pytest.raises(SchemaError, match="not a cable core"):
        core_colour(plant.model(), make_id(Conductor, ("carried",)))


def test_a_core_of_a_cable_with_no_product_raises() -> None:
    # MUTATION: `_product_colours` returns `("",)` instead of `()` for a cable with no part
    plant, _, cable = _plant(None)
    core = _core(plant, cable, 1)
    with pytest.raises(SchemaError, match="outside its cable product's 0 core colour"):
        core_colour(plant.model(), core)


def test_a_core_with_no_core_facet_raises() -> None:
    # MUTATION: `core_colour` falls back to `colours[0]` when it finds no `core` facet
    plant, _, cable = _plant()
    core = _core(plant, cable, None)
    with pytest.raises(SchemaError, match="no `core` facet"):
        core_colour(plant.model(), core)


def test_an_unknown_conductor_raises() -> None:
    # MUTATION: `core_colour` reads `conductors(model)[conductor]` past `require` (a KeyError)
    plant, _, _ = _plant()
    with pytest.raises(SchemaError):
        core_colour(plant.model(), Id(kind="conductor", value="f" * 32))


def test_every_cable_row_has_the_colour_core_colour_gives() -> None:
    # MUTATION: `cable_rows` reads `colours[index]`, or a colour of its own, instead of `_colour_at`
    plant, _, cable = _plant()
    for index in (3, 1, 2):
        _core(plant, cable, index)
    model = plant.model()
    rows = cable_rows(model, cable)
    assert [row.colour for row in rows] == list(_COLOURS)
    assert all(row.colour == core_colour(model, row.conductor) for row in rows)


def _colour_and_label(model: Model, harness: Id[Item]) -> tuple[str, str | None]:
    (harness_cable,) = harness_cables(model, harness)
    (core,) = harness_cable.cores
    return core.colour, core.label


def test_no_reader_takes_a_cores_colour_from_a_wire_facet() -> None:
    """A `wire` facet on a core carries a label and a colour; only the label is read (SC4)."""
    # MUTATION: `cable_rows` (or `_cores`) prefers the core's `wire` facet colour when it has one
    plant, harness, cable = _plant(("BU",))
    core = _core(plant, cable, 1)
    plant.add(
        WireFacet(
            id=make_id(WireFacet, ("core-1", "wire")),
            key=("core-1", "wire"),
            subject=core,
            colour="RD",
            gauge_mm2=Decimal("0.5"),
            length_mm=None,
            label="X",
        )
    )
    model = plant.model()
    (row,) = cable_rows(model, cable)
    assert row.colour == "BU"
    assert core_colour(model, core) == "BU"
    assert _colour_and_label(model, harness) == ("BU", "X")
