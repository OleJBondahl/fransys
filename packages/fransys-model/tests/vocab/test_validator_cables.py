"""WP13 tests: `validators.cables` (ROADMAP WP13, design/facets.md)."""

from decimal import Decimal
from unittest.mock import patch

from scaffold import scaffold

from fransys_model.kernel import Draft, Id, Model, Origin, Record, freeze
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import ConductorKind, PartCategory
from fransys_model.vocab.facets.cable import CableProductFacet, CoreFacet
from fransys_model.vocab.templates import Part
from fransys_model.vocab.validators.cables import CABLE_CORE_COUNT, check_cables

_CARRIER = Id(kind="item", value="9" * 32)


def _freeze(records: tuple[Record, ...]) -> Model:
    draft = Draft()
    origin = Origin(file="test_validator_cables.py", line=1, note="fixture")
    draft.extend((*records, *scaffold(records)), origin=origin)
    return freeze(draft)


def _cable_4core_part() -> tuple[Part, CableProductFacet]:
    part = Part(
        id=Id(kind="part", value="1" * 32),
        key=("examples", "cable_4core"),
        mpn="EXAMPLE-CABLE-4G1.5",
        manufacturer="Example Co",
        description="",
        category=PartCategory.CABLE,
        class_code="W",
    )
    product = CableProductFacet(
        id=Id(kind="facet.cable_product", value="2" * 32),
        key=("examples", "cable_4core", "cable_product"),
        subject=part.id,
        core_colours=("brown", "black", "grey", "blue"),
        gauge_mm2=Decimal("1.5"),
        shielded=False,
    )
    return part, product


def _cable(part: Part) -> Item:
    """Setup only: the cable item the cores are carried by, of the cable part."""
    return Item(
        id=_CARRIER,
        key=("examples", "w012"),
        part=part.id,
        parent=None,
        position=None,
        tag=None,
        description="",
    )


def _core(index: int) -> tuple[Conductor, CoreFacet]:
    conductor = Conductor(
        id=Id(kind="conductor", value=str(index) * 32),
        key=("examples", "w012", f"core-{index}"),
        a=Id(kind="port", value=f"{index}a".zfill(32)),
        b=Id(kind="port", value=f"{index}b".zfill(32)),
        kind=ConductorKind.CORE,
        carrier=_CARRIER,
    )
    facet = CoreFacet(
        id=Id(kind="facet.core", value=f"{index}c".zfill(32)),
        key=("examples", "w012", f"core-{index}", "core"),
        subject=conductor.id,
        index=index,
    )
    return conductor, facet


def test_cable_with_the_declared_core_count_has_no_finding() -> None:
    """A 4-core cable carrying exactly 4 `core`-kind conductors matches its product."""
    part, product = _cable_4core_part()
    cores = [_core(n) for n in range(1, len(product.core_colours) + 1)]
    records = (part, product, _cable(part), *[record for pair in cores for record in pair])
    findings = check_cables(_freeze(records))
    assert not [f for f in findings if f.code == CABLE_CORE_COUNT]


def test_cable_with_too_few_cores_yields_cable_core_count() -> None:
    """A 4-core cable carrying only 3 `core`-kind conductors yields `CABLE_CORE_COUNT`."""
    part, product = _cable_4core_part()
    cores = [_core(n) for n in range(1, 4)]
    records = (part, product, _cable(part), *[record for pair in cores for record in pair])
    findings = check_cables(_freeze(records))
    assert any(f.code == CABLE_CORE_COUNT for f in findings)


def test_check_cables_calls_the_shared_is_cable() -> None:
    """RW4 (decision model-0108): `check_cables` calls `is_cable`, never its own copy of "is
    this a cable" (root CLAUDE.md's own red flag, "one rule computed in two places"). Behaviour
    is unchanged either way -- `is_cable` and the old `products.get(cable.part) is not None`
    guard read the same `CableProductFacet.subject` source -- so this is a delegation proof, not
    a behaviour-differencing one, the same shape `test_validator_harness_without_tag.py`'s own
    `test_the_validator_calls_the_shared_has_own_designation` uses."""
    import fransys_model.vocab.validators.cables as module

    part, product = _cable_4core_part()
    records = (part, product, _cable(part))
    model = _freeze(records)
    with patch.object(module, "is_cable", wraps=module.is_cable) as spy:
        check_cables(model)
    assert spy.call_count >= 1
    assert any(call.args[1] == _CARRIER for call in spy.call_args_list)
