"""FD1, FD5 (fixed-designations spec): a `facet.reserved_designation` text is never reused.

`_assigned` puts every group's reserved texts into `taken` before counting up, and
`_duplicates` widens from tags alone to every own text (tag or assigned), plus the group's
reserved texts.
"""

from plant import Plant

from fransys_model.derive import item_designation
from fransys_model.derive.passes.numbering import DESIGNATION_DUPLICATE, number
from fransys_model.kernel import Id, make_id
from fransys_model.vocab.core import Item, UnitRelease
from fransys_model.vocab.facets.assigned_designation import AssignedDesignationFacet
from fransys_model.vocab.facets.reserved_designation import ReservedDesignationFacet


def _item_id(key: str) -> Id[Item]:
    return make_id(Item, (key,))


def _reserved(
    release: Id[UnitRelease], *, code: str, text: str, tag: str = "reserved"
) -> ReservedDesignationFacet:
    key = ("reserved", tag)
    return ReservedDesignationFacet(
        id=make_id(ReservedDesignationFacet, key),
        key=key,
        subject=release,
        scope=None,
        code=code,
        text=text,
    )


def test_a_reserved_text_is_never_reused_when_numbering_a_new_sibling() -> None:
    """`coil-a` is pinned `K1`; `K2` is reserved (retired); the untagged `aux` gets `K3`."""
    plant = Plant()
    relay = plant.part("K")
    release = plant.release()
    unit = plant.unit("board", parent=None)
    plant.item("coil-a", part=relay, designation="K1", unit=unit)
    plant.item("aux", part=relay, unit=unit)
    plant.add(_reserved(release, code="K", text="K2"))
    numbered, findings = number(plant.model())
    assert findings == ()
    assert item_designation(numbered, _item_id("aux")) == "K3"


def test_a_tag_equal_to_a_reserved_text_is_a_duplicate() -> None:
    """A tag equal to a released, retired text is `DESIGNATION_DUPLICATE`, naming the text."""
    plant = Plant()
    relay = plant.part("K")
    release = plant.release()
    unit = plant.unit("board", parent=None)
    plant.item("dup", part=relay, designation="K2", unit=unit)
    plant.add(_reserved(release, code="K", text="K2"))
    _, findings = number(plant.model())
    assert len(findings) == 1
    finding = findings[0]
    assert finding.code == DESIGNATION_DUPLICATE
    assert finding.subjects == (_item_id("dup"),)
    assert "K2" in finding.message


def test_a_tag_equal_to_another_items_assigned_text_is_a_duplicate() -> None:
    """A tag equal to a sibling's pre-existing assigned text is caught, subject the tagged item.

    Before FD5's widening, `_duplicates` counted tags only, so a tag equal to an
    ALREADY-DISTINCT assigned text (never authored, never a tag) went unreported
    (model-0086 / SCHEMA-3's own note). Item A (`k-a`) carries a pre-seeded
    `facet.assigned_designation(text="K1")`; item B (`k-b`) is tagged `K1`.
    """
    plant = Plant()
    relay = plant.part("K")
    plant.item("k-a", part=relay)
    plant.item("k-b", part=relay, designation="K1")
    facet_key = ("k-a", "assigned_designation")
    plant.add(
        AssignedDesignationFacet(
            id=make_id(AssignedDesignationFacet, facet_key),
            key=facet_key,
            subject=_item_id("k-a"),
            text="K1",
        )
    )
    _, findings = number(plant.model())
    subjects = {finding.subjects for finding in findings if finding.code == DESIGNATION_DUPLICATE}
    assert (_item_id("k-b"),) in subjects
