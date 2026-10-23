"""EARTH-12: a core that is not GNYE on a PE-role port is one fact, and one ERROR check."""

from decimal import Decimal

import pytest
from plant import Plant
from query_builders import make_part, make_pin

from fransys_model.checks.earth import CORE_ON_PE_NOT_GNYE, check_earth
from fransys_model.derive import core_on_pe_not_gnye
from fransys_model.kernel import Severity, make_id
from fransys_model.vocab.core import Item, Port
from fransys_model.vocab.enums import PartCategory, PortRole
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet, CoreFacet


@pytest.mark.parametrize(
    ("colour", "roles", "expected"),
    [
        ("BN", [PortRole.PE], True),
        ("BN", [PortRole.GENERIC, PortRole.PE], True),
        ("GNYE", [PortRole.PE], False),
        ("SH", [PortRole.PE], False),
        ("BN", [PortRole.GENERIC], False),
        ("BN", [], False),
    ],
)
def test_the_fact_is_a_non_gnye_colour_with_a_pe_role(
    colour: str, roles: list[PortRole], *, expected: bool
) -> None:
    assert core_on_pe_not_gnye(colour, roles) is expected


def _findings(colour: str) -> list[tuple[str, Severity]]:
    """A one-core cable of `colour` whose core ends on a PE-role port."""
    plant = Plant()
    part = make_part(plant, "cab", "MPN-cab", category=PartCategory.CABLE)
    plant.add(
        CableProductFacet(
            id=make_id(CableProductFacet, ("cab", "product")),
            key=("cab", "product"),
            subject=part,
            core_colours=(colour,),
            gauge_mm2=Decimal("0.5"),
            shielded=False,
            pairs=(),
        )
    )
    cable = plant.item("w1", designation="W1", part=part)
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w1", "c")), key=("w1", "c"), subject=cable, length_mm=None
        )
    )
    function = plant.function(plant.item("m1"), "motor")
    key = ("m1", "motor", "PE")
    pe = Port(
        id=make_id(Port, key), key=key, function=function, template=None, name="PE",
        role=PortRole.PE,
    )  # fmt: skip
    plant.add(pe)
    core = plant.core(pe.id, make_pin(plant, "b", "B"), key="c1", carrier=make_id(Item, ("w1",)))
    plant.add(CoreFacet(id=make_id(CoreFacet, ("c1", "f")), key=("c1", "f"), subject=core, index=1))
    return [
        (f.code, f.severity) for f in check_earth(plant.model()) if f.code == CORE_ON_PE_NOT_GNYE
    ]


def test_a_non_gnye_core_on_a_pe_port_is_an_error() -> None:
    # MUTATION: `core_on_pe_not_gnye` compares `==` GNYE, or `check_earth` skips `_core_findings`
    assert _findings("BN") == [(CORE_ON_PE_NOT_GNYE, Severity.ERROR)]


def test_a_gnye_core_on_a_pe_port_is_silent() -> None:
    assert _findings("GNYE") == []


def test_a_screen_on_a_pe_port_is_silent() -> None:
    # MUTATION: `core_on_pe_not_gnye` drops the `SH` exemption
    assert _findings("SH") == []
    assert _findings("BN") != []
