"""Tests for `validators.harness_without_tag` (decision model-0107)."""

from decimal import Decimal
from typing import Any
from unittest.mock import patch

from fransys_model.derive import designation
from fransys_model.kernel import Draft, Model, Origin, Record, Severity, freeze, make_id
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import PartCategory
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet
from fransys_model.vocab.templates import Part
from fransys_model.vocab.validators import ALL_VALIDATORS, check_harness_without_tag
from fransys_model.vocab.validators.harness_without_tag import HARNESS_WITHOUT_TAG


def _freeze(records: tuple[Record, ...]) -> Model:
    draft = Draft()
    origin = Origin(file="test_validator_harness_without_tag.py", line=1, note="fixture")
    draft.extend(records, origin=origin)
    return freeze(draft)


def _item(name: str, *, tag: str | None, parent: Any = None) -> Item:
    return Item(
        id=make_id(Item, (name,)),
        key=(name,),
        part=None,
        parent=parent,
        position=None,
        tag=tag,
        description="Invented",
    )


def _cable_facet(item: Item) -> CableFacet:
    key = (*item.key, "cable")
    return CableFacet(id=make_id(CableFacet, key), key=key, subject=item.id, length_mm=None)


def _cable_part() -> tuple[Part, CableProductFacet]:
    """A cable `Part` (decision model-0108) with its `cable_product` facet."""
    part = Part(
        id=make_id(Part, ("w0c", "part")),
        key=("w0c", "part"),
        mpn="MPN-w0c",
        manufacturer="Example Co",
        description="Invented w0c",
        category=PartCategory.CABLE,
        class_code="W",
    )
    product = CableProductFacet(
        id=make_id(CableProductFacet, ("w0c", "part", "product")),
        key=("w0c", "part", "product"),
        subject=part.id,
        core_colours=(),
        gauge_mm2=Decimal("0.5"),
        shielded=False,
    )
    return part, product


def _harness_and_cable(*, harness_tag: str | None) -> tuple[Item, Item, tuple[Record, ...]]:
    """A container item with one cable-faceted child: structurally a harness (H2)."""
    harness = _item("w0", tag=harness_tag)
    part, product = _cable_part()
    cable = Item(
        id=make_id(Item, ("w0c",)),
        key=("w0c",),
        part=part.id,
        parent=harness.id,
        position=None,
        tag=None,
        description="Invented",
    )
    return harness, cable, (harness, part, product, cable, _cable_facet(cable))


def test_an_untagged_structural_harness_yields_one_harness_without_tag() -> None:
    harness, _cable, records = _harness_and_cable(harness_tag=None)
    model = _freeze(records)
    (finding,) = check_harness_without_tag(model)
    assert finding.code == HARNESS_WITHOUT_TAG
    assert finding.severity is Severity.ERROR
    assert finding.subjects == (harness.id,)
    assert "w0" in finding.message
    assert "tag" in finding.message


def test_a_tagged_structural_harness_yields_nothing() -> None:
    """Clean twin: a harness with its own tag has a designation and is not reported."""
    _harness, _cable, records = _harness_and_cable(harness_tag="W3")
    model = _freeze(records)
    assert check_harness_without_tag(model) == ()


def test_a_container_with_no_cable_child_is_not_a_harness_and_yields_nothing() -> None:
    """Guard: an untagged, part-less container with no cable child is not `is_harness`."""
    plain = _item("box", tag=None)
    model = _freeze((plain,))
    assert check_harness_without_tag(model) == ()


def test_check_harness_without_tag_is_registered_in_all_validators() -> None:
    assert check_harness_without_tag in ALL_VALIDATORS


def test_the_validator_calls_the_shared_has_own_designation() -> None:
    """model-0107: the validator calls `vocab.own_designation.has_own_designation`, never its
    own copy of the tag-or-facet check.
    """
    import fransys_model.vocab.validators.harness_without_tag as module

    harness, _cable, records = _harness_and_cable(harness_tag=None)
    model = _freeze(records)
    with patch.object(module, "has_own_designation", wraps=module.has_own_designation) as spy:
        check_harness_without_tag(model)
    assert spy.call_count >= 1
    assert any(call.args[1].id == harness.id for call in spy.call_args_list)


def test_own_designation_or_none_calls_the_shared_has_own_designation() -> None:
    """model-0107: `derive.designation.own_designation_or_none` calls the same shared
    predicate for an untagged item, never re-deriving the tag-or-facet check itself.
    """
    harness, _cable, records = _harness_and_cable(harness_tag=None)
    model = _freeze(records)
    with patch.object(
        designation, "has_own_designation", wraps=designation.has_own_designation
    ) as spy:
        result = designation.own_designation_or_none(model, harness)
    assert result is None
    assert spy.call_count == 1
    assert spy.call_args.args[1].id == harness.id
