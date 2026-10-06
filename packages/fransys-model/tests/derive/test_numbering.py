"""WP14 tests: `derive.passes.numbering` (ROADMAP WP14, design/derive.md)."""

from derive_helpers import add_all

from fransys_model.derive import item_designation
from fransys_model.derive.passes.numbering import DESIGNATION_DUPLICATE, number
from fransys_model.kernel import Draft, Id, Origin, freeze
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import PartCategory
from fransys_model.vocab.facets.assigned_designation import AssignedDesignationFacet
from fransys_model.vocab.tables import facets_of
from fransys_model.vocab.tables import items as items_of
from fransys_model.vocab.templates import Part

_PART = Part(
    id=Id(kind="part", value="1" * 32),
    key=("contactor",),
    mpn="SIM-CONTACTOR-9A",
    manufacturer="Synthetic Parts Co",
    description="9A contactor",
    category=PartCategory.ELECTROMECHANICAL,
    class_code="K",
)


def _item(value: str, key: tuple[str, ...], *, designation: str | None) -> Item:
    return Item(
        id=Id(kind="item", value=value * 32),
        key=key,
        part=_PART.id,
        parent=None,
        position=None,
        tag=designation,
        description="pump starter",
    )


def test_numbering_is_independent_of_insertion_order(origin: Origin) -> None:
    """Numbering two unnumbered items gives the same digest, whichever order they're authored in."""
    item_a = _item("a", ("k-a",), designation=None)
    item_b = _item("b", ("k-b",), designation=None)

    forward = Draft()
    add_all(forward, _PART, item_a, item_b, origin=origin)
    reversed_draft = Draft()
    add_all(reversed_draft, _PART, item_b, item_a, origin=origin)

    forward_model, _ = number(freeze(forward))
    reversed_model, _ = number(freeze(reversed_draft))
    assert forward_model.digest == reversed_model.digest


def test_numbering_never_overwrites_an_authored_designation(origin: Origin) -> None:
    """An item authored with `designation="K5"` keeps it exactly, untouched by the counter."""
    item = _item("a", ("k-a",), designation="K5")
    draft = Draft()
    add_all(draft, _PART, item, origin=origin)
    model = freeze(draft)
    numbered, _findings = number(model)
    assert items_of(numbered)[item.id].tag == "K5"
    assert item_designation(numbered, item.id) == "K5"
    assert facets_of(numbered, AssignedDesignationFacet) == {}


def test_numbering_duplicate_authored_designation_is_a_finding(origin: Origin) -> None:
    """Two items in one scope authored with the same designation each get a finding, not a fix."""
    item_a = _item("a", ("k-a",), designation="K1")
    item_b = _item("b", ("k-b",), designation="K1")
    draft = Draft()
    add_all(draft, _PART, item_a, item_b, origin=origin)
    model = freeze(draft)
    numbered, findings = number(model)
    assert any(f.code == DESIGNATION_DUPLICATE for f in findings)
    assert items_of(numbered)[item_a.id].tag == "K1"
    assert items_of(numbered)[item_b.id].tag == "K1"
    assert item_designation(numbered, item_a.id) == "K1"
    assert item_designation(numbered, item_b.id) == "K1"
    assert facets_of(numbered, AssignedDesignationFacet) == {}
