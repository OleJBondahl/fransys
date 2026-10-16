"""Tests: the typed accessors for the string facts (M8): unit box, band rank, subject kind."""

from plant import Plant

from fransys_model.derive.facts.subjects import is_unit_boundary, subject_kind
from fransys_model.kernel import make_id
from fransys_model.layout.band_rank import band_rank
from fransys_model.layout.formats import default_profile
from fransys_model.vocab.connectivity import Net
from fransys_model.vocab.core import Item, Unit
from fransys_model.vocab.enums import SubjectKind


def test_a_unit_box_is_a_unit_boundary_and_an_item_box_is_not() -> None:
    """The box key's kind text decides, through one function."""
    assert is_unit_boundary(make_id(Unit, ("u1",)))
    assert not is_unit_boundary(make_id(Item, ("i1",)))


def test_band_rank_reads_the_house_profile_and_none_for_an_unranked_key() -> None:
    """`supply` 0, `coil` 4, `terminal.last` 5; an unranked key or no band is `None`."""
    profile = default_profile()
    assert band_rank(profile, "supply") == 0
    assert band_rank(profile, "coil") == 4
    assert band_rank(profile, "terminal.last") == 5
    assert band_rank(profile, "bar") is None
    assert band_rank(profile, None) is None


def test_subject_kind_of_an_item_a_port_and_a_conductor_handle() -> None:
    """Each handle names its kind; a net is `OTHER`."""
    plant = Plant()
    a = plant.pin("i", "f", "1")
    b = plant.pin("j", "f", "1")
    wire = plant.wire(a, b, key="w")
    assert subject_kind(make_id(Item, ("i",))) is SubjectKind.ITEM
    assert subject_kind(a) is SubjectKind.PORT
    assert subject_kind(wire) is SubjectKind.CONDUCTOR
    assert subject_kind(make_id(Net, ("n",))) is SubjectKind.OTHER
