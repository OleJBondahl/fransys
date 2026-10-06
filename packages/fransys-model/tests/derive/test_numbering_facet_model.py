"""SC3 acceptance 3: the numbering pass writes `facet.assigned_designation`, never an item."""

from plant import Plant

from fransys_model.derive import item_designation
from fransys_model.derive.passes.numbering import number
from fransys_model.kernel import Id, Model, Origin, evolve, make_id
from fransys_model.vocab.core import Item
from fransys_model.vocab.facets.assigned_designation import AssignedDesignationFacet
from fransys_model.vocab.tables import facets_of, items

_ORIGIN = Origin(file="test_numbering_facet_model.py", line=1, note="evolve")


def _item_id(key: str) -> Id[Item]:
    return make_id(Item, (key,))


def _assigned(model: Model) -> dict[str, str]:
    """The assigned text by the subject item's authoring key."""
    return {
        "/".join(items(model)[facet.subject].key): facet.text
        for facet in facets_of(model, AssignedDesignationFacet).values()
    }


def _facet(key: str, text: str) -> AssignedDesignationFacet:
    facet_key = (key, "assigned_designation")
    return AssignedDesignationFacet(
        id=make_id(AssignedDesignationFacet, facet_key),
        key=facet_key,
        subject=_item_id(key),
        text=text,
    )


def test_each_numbered_item_gets_one_assigned_facet_and_a_tagged_item_none() -> None:
    """Two class-K and one class-Q item become `K1`, `K2`, `Q1`; a tagged `K9` gets no facet."""
    plant = Plant()
    relay, breaker = plant.part("K"), plant.part("Q")
    plant.item("k-a", part=relay)
    plant.item("k-b", part=relay)
    plant.item("q-a", part=breaker)
    plant.item("k-tagged", part=relay, designation="K9")
    numbered, findings = number(plant.model())
    assert findings == ()
    facets = facets_of(numbered, AssignedDesignationFacet)
    assert len(facets) == 3
    assert _assigned(numbered) == {"k-a": "K1", "k-b": "K2", "q-a": "Q1"}
    for facet in facets.values():
        assert facet.key == (*items(numbered)[facet.subject].key, "assigned_designation")
    for key, text in (("k-a", "K1"), ("k-b", "K2"), ("q-a", "Q1")):
        assert items(numbered)[_item_id(key)].tag is None
        assert item_designation(numbered, _item_id(key)) == text
    assert items(numbered)[_item_id("k-tagged")].tag == "K9"
    assert item_designation(numbered, _item_id("k-tagged")) == "K9"


def test_a_second_run_of_the_pass_returns_the_same_model_with_the_same_facets() -> None:
    """Nothing is left to number after the first run: same object, same digest, same facets."""
    plant = Plant()
    relay = plant.part("K")
    plant.item("k-a", part=relay)
    plant.item("k-b", part=relay)
    first, _ = number(plant.model())
    second, findings = number(first)
    assert second is first
    assert second.digest == first.digest
    assert findings == ()
    assert facets_of(second, AssignedDesignationFacet) == facets_of(first, AssignedDesignationFacet)
    assert _assigned(second) == {"k-a": "K1", "k-b": "K2"}


def test_an_item_added_after_numbering_takes_the_next_free_number_and_the_others_keep_theirs() -> (
    None
):
    """`K3` after `K1` and `K2`; the two existing facets are the same records as before."""
    plant = Plant()
    relay = plant.part("K")
    plant.item("k-a", part=relay)
    plant.item("k-b", part=relay)
    first, _ = number(plant.model())
    before = dict(facets_of(first, AssignedDesignationFacet))
    new_item = Item(
        id=_item_id("k-c"),
        key=("k-c",),
        part=relay,
        parent=None,
        position=None,
        tag=None,
        description="Invented",
    )
    grown = evolve(first, put=[new_item], origin=_ORIGIN)
    second, _ = number(grown)
    after = facets_of(second, AssignedDesignationFacet)
    assert _assigned(second) == {"k-a": "K1", "k-b": "K2", "k-c": "K3"}
    assert len(after) == 3
    for facet_id, facet in before.items():
        assert after[facet_id] == facet
    assert item_designation(second, _item_id("k-c")) == "K3"


def test_an_existing_assigned_designation_is_kept_and_its_text_counts_as_taken() -> None:
    """A holds a `K1` facet before the pass: it stays as it is, and untagged sibling B gets `K2`."""
    plant = Plant()
    relay = plant.part("K")
    plant.item("k-a", part=relay)
    plant.item("k-b", part=relay)
    existing = _facet("k-a", "K1")
    plant.add(existing)
    numbered, _ = number(plant.model())
    facets = facets_of(numbered, AssignedDesignationFacet)
    assert facets[existing.id] == existing
    assert set(facets) == {
        existing.id,
        make_id(AssignedDesignationFacet, ("k-b", "assigned_designation")),
    }
    assert _assigned(numbered) == {"k-a": "K1", "k-b": "K2"}
    assert item_designation(numbered, _item_id("k-b")) == "K2"


def test_an_authored_tag_counts_as_taken_so_an_untagged_sibling_skips_it() -> None:
    """A is authored `K1`; untagged sibling B of the same class gets `K2`, and A gets no facet."""
    plant = Plant()
    relay = plant.part("K")
    plant.item("k-a", part=relay, designation="K1")
    plant.item("k-b", part=relay)
    numbered, findings = number(plant.model())
    assert findings == ()
    assert _assigned(numbered) == {"k-b": "K2"}
    assert item_designation(numbered, _item_id("k-a")) == "K1"
    assert item_designation(numbered, _item_id("k-b")) == "K2"
