"""WP13 tests: both finding codes of `check_cables`, firing and not firing (design/facets.md)."""

import dataclasses
import re
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from plant import Plant

from fransys_model.kernel import Finding, Id, Model, Severity, make_id
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.enums import ConductorKind, PartCategory
from fransys_model.vocab.facets.cable import CableProductFacet, CoreFacet
from fransys_model.vocab.templates import Part
from fransys_model.vocab.validators.cables import (
    CABLE_CORE_COUNT,
    check_cables,
)

if TYPE_CHECKING:
    from fransys_model.vocab.core import Item

_COLOURS = ("brown", "black", "grey", "blue")


def _cable_part(
    plant: Plant, key: str = "cable_4core", colours: tuple[str, ...] = _COLOURS
) -> Id[Part]:
    part = Part(
        id=make_id(Part, (key,)),
        key=(key,),
        mpn=f"EXAMPLE-{key}",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.CABLE,
        class_code="W",
    )
    product = CableProductFacet(
        id=make_id(CableProductFacet, (key, "product")),
        key=(key, "product"),
        subject=part.id,
        core_colours=colours,
        gauge_mm2=Decimal("1.5"),
        shielded=False,
    )
    plant.add(part, product)
    return part.id


def _core(
    plant: Plant, cable: Id[Item], number: int, colour: str | None, *, cable_name: str = "w012"
) -> Id[Any]:
    """A core conductor carried by `cable`, with a `core` facet unless `colour` is None."""
    a = plant.pin(f"{cable_name}-a{number}", "f", "1")
    b = plant.pin(f"{cable_name}-b{number}", "f", "1")
    core = plant.core(a, b, key=f"{cable_name}-core-{number}", carrier=cable)
    if colour is not None:
        plant.add(
            CoreFacet(
                id=make_id(CoreFacet, (cable_name, str(number))),
                key=(cable_name, str(number)),
                subject=core,
                index=number,
            )
        )
    return core


def _of(plant: Plant, code: str) -> list[Finding]:
    return [f for f in check_cables(plant.model()) if f.code == code]


# ---- CABLE_CORE_COUNT ---------------------------------------------------------------------


def test_the_declared_number_of_cores_is_no_finding() -> None:
    """Four cores on a four-core cable."""
    plant = Plant()
    cable = plant.item("w012", part=_cable_part(plant))
    for number, colour in enumerate(_COLOURS):
        _core(plant, cable, number, colour)
    assert check_cables(plant.model()) == ()


def test_fewer_cores_than_the_product_is_a_warning_naming_the_cable_and_product() -> None:
    """Cores may not be modelled yet: `WARNING`."""
    plant = Plant()
    cable = plant.item("w012", part=_cable_part(plant))
    for number in range(3):
        _core(plant, cable, number, _COLOURS[number])
    (finding,) = _of(plant, CABLE_CORE_COUNT)
    assert finding.severity is Severity.WARNING
    assert finding.subjects == tuple(
        sorted((cable, make_id(CableProductFacet, ("cable_4core", "product"))))
    )
    assert "carries 3 cores" in finding.message
    assert "has 4" in finding.message


def test_more_cores_than_the_product_is_an_error() -> None:
    """A product cannot have more cores than it has."""
    plant = Plant()
    cable = plant.item("w012", part=_cable_part(plant, colours=("brown", "black")))
    for number, colour in enumerate(("brown", "black", "brown")):
        _core(plant, cable, number, colour)
    (finding,) = _of(plant, CABLE_CORE_COUNT)
    assert finding.severity is Severity.ERROR
    assert "carries 3 cores" in finding.message


def test_a_cable_with_no_cores_at_all_is_a_count_finding() -> None:
    """Zero is a count too."""
    plant = Plant()
    plant.item("w012", part=_cable_part(plant))
    (finding,) = _of(plant, CABLE_CORE_COUNT)
    assert "carries 0 cores" in finding.message


def test_only_core_kind_conductors_carried_by_the_cable_count() -> None:
    """A wire naming the cable, another cable's core and a core with no carrier: none count."""
    plant = Plant()
    part = _cable_part(plant, colours=("brown", "black"))
    cable = plant.item("w012", part=part)
    other = plant.item("w013", part=part)
    for number, colour in enumerate(("brown", "black")):
        _core(plant, cable, number, colour)
    _core(plant, other, 0, "brown", cable_name="w013")
    a, b = plant.pin("x-a", "f", "1"), plant.pin("x-b", "f", "1")
    plant.add(
        Conductor(
            id=make_id(Conductor, ("wire-with-carrier",)),
            key=("wire-with-carrier",),
            a=a,
            b=b,
            kind=ConductorKind.WIRE,
            carrier=cable,
        )
    )
    c, d = plant.pin("y-a", "f", "1"), plant.pin("y-b", "f", "1")
    plant.wire(c, d, key="core-without-carrier", kind=ConductorKind.CORE)
    counts = _of(plant, CABLE_CORE_COUNT)
    assert len(counts) == 1  # only the other cable, short of one core
    assert "w013" in counts[0].message


def test_an_item_whose_part_has_no_cable_product_is_not_a_cable() -> None:
    """Nothing to compare with."""
    plant = Plant()
    part, *_ = plant.relay_part()
    plant.item("k1", part=part.id)
    assert check_cables(plant.model()) == ()


def test_two_cables_are_checked_each_against_its_own_product() -> None:
    """A two-core and a four-core cable, both complete."""
    plant = Plant()
    two = plant.item("w1", part=_cable_part(plant, "two", ("brown", "blue")))
    four = plant.item("w2", part=_cable_part(plant, "four"))
    for number, colour in enumerate(("brown", "blue")):
        _core(plant, two, number, colour, cable_name="w1")
    for number, colour in enumerate(_COLOURS):
        _core(plant, four, number, colour, cable_name="w2")
    assert check_cables(plant.model()) == ()


# ---- the shape of the result --------------------------------------------------------------


def _mixed() -> Plant:
    plant = Plant()
    cable = plant.item("w012", part=_cable_part(plant))
    _core(plant, cable, 1, "pink")
    _core(plant, cable, 2, "brown")
    return plant


def test_findings_are_sorted() -> None:
    """Sorted by `(code, subjects, message)`."""
    findings = check_cables(_mixed().model())
    assert {f.code for f in findings} == {CABLE_CORE_COUNT}
    assert findings == tuple(sorted(findings, key=lambda f: (f.code, f.subjects, f.message)))


def test_the_findings_do_not_depend_on_the_order_of_a_models_tables() -> None:
    """Tables backwards: the same findings."""
    model = _mixed().model()
    backwards: Model = dataclasses.replace(
        model,
        digest="reversed-tables-test-cables-findings",  # unique: the caches key on digest
        tables=frozendict(
            {
                kind: frozendict(reversed(table.items()))
                for kind, table in reversed(model.tables.items())
            }
        ),
    )
    assert check_cables(backwards) == check_cables(model)


def test_no_message_prints_an_id() -> None:
    """Messages name keys and colours."""
    for finding in check_cables(_mixed().model()):
        assert not re.search(r"[0-9a-f]{32}", finding.message)


def test_an_empty_model_has_no_finding() -> None:
    """Nothing to check."""
    assert check_cables(Plant().model()) == ()
