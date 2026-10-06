"""RATINGS-1 step 2, part 3: the fallback rule and the typed readers (decision model-0079).

A function takes its template's rating, else its part's, whole and never per field. The readers
answer from one index per model digest.
"""

from decimal import Decimal
from typing import Any

import pytest
from examples import cable_4_core_part, core_model, relay_part_bundle

from fransys_model import derive, vocab
from fransys_model.kernel import Id, Model, Origin, freeze, make_id, merge
from fransys_model.vocab import (
    FunctionKind,
    Operating,
    OperatingFacet,
    PartRatingFacet,
    Rating,
    RatingFacet,
    effective_rating,
    function_operating,
    function_rating,
    part_rating,
)
from fransys_model.vocab import rating_readers as readers
from fransys_model.vocab.core import Function
from fransys_model.vocab.templates import FunctionTemplate, Part

_ORIGIN = Origin(file="test_rating_readers.py", line=1, note="fixture")
_RELAY = relay_part_bundle().part.id
_COIL_T = make_id(FunctionTemplate, ("examples", "relay", "fn", "coil"))
_NO_1_T = make_id(FunctionTemplate, ("examples", "relay", "fn", "no_1"))
_CABLE = cable_4_core_part()

_COIL = make_id(Function, ("plant", "k1", "fn", "coil"))
_CONTACT = make_id(Function, ("plant", "k1", "fn", "no_1"))
_BARE = make_id(Function, ("plant", "k1", "fn", "bare"))
_HOUSING_J1 = make_id(Function, ("plant", "housing", "j1"))
_UNKNOWN = make_id(Function, ("plant", "nowhere"))

_AC = Rating(voltage_ac_v=Decimal(250), current_ac_a=Decimal("0.5"))
_DC = Rating(voltage_dc_v=Decimal(60), current_dc_a=Decimal(2))
_PART_ONLY = Rating(voltage_ac_v=Decimal(500), voltage_dc_v=Decimal(48))
_OPERATING = Operating(nominal_voltage_v=Decimal(24), min_voltage_v=Decimal(18))


def _function(key: tuple[str, ...], template: Id[FunctionTemplate] | None) -> Function:
    return Function(
        id=make_id(Function, key),
        key=key,
        item=make_id(vocab.Item, ("plant", "k1")),
        template=template,
        name=key[-1],
        kind=FunctionKind.CONTACT_NO,
    )


def _model(*records: Any) -> Model:
    draft = merge(core_model())
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def _facet(cls: type, tag: str, subject: Id[Any], value: Any) -> Any:
    key = ("ratings", tag)
    field = "operating" if cls is OperatingFacet else "rating"
    return cls(id=make_id(cls, key), key=key, subject=subject, **{field: value})


_CONTACTS = (
    _function(("plant", "k1", "fn", "no_1"), _NO_1_T),
    _function(("plant", "k1", "fn", "bare"), None),
)
_TEMPLATE_RATING = _facet(RatingFacet, "coil", _COIL_T, _AC)
_PART_RATING = _facet(PartRatingFacet, "relay", _RELAY, _PART_ONLY)
_COIL_OPERATING = _facet(OperatingFacet, "coil", _COIL_T, _OPERATING)
_CABLE_RECORDS = (_CABLE, _facet(PartRatingFacet, "cable", _CABLE.id, _DC))


@pytest.fixture
def full() -> Model:
    """The relay's coil template and its part both rated; a contact and a bare function added."""
    return _model(*_CONTACTS, *_CABLE_RECORDS, _TEMPLATE_RATING, _PART_RATING, _COIL_OPERATING)


@pytest.fixture
def without_template_rating() -> Model:
    """The same model with the coil template's `RatingFacet` left out."""
    return _model(*_CONTACTS, *_CABLE_RECORDS, _PART_RATING, _COIL_OPERATING)


def test_effective_rating_takes_the_template_when_it_has_one() -> None:
    """Both set: the template's; the part's is ignored."""
    assert effective_rating(_AC, _PART_ONLY) is _AC


def test_effective_rating_falls_back_to_the_part_then_to_none() -> None:
    """No template rating: the part's; neither: `None`."""
    assert effective_rating(None, _PART_ONLY) is _PART_ONLY
    assert effective_rating(None, None) is None


def test_effective_rating_replaces_the_whole_record_never_a_field() -> None:
    """A template with only AC hides the part's DC: the result's DC is `None`."""
    result = effective_rating(_AC, _PART_ONLY)
    assert result is not None
    assert result.voltage_dc_v is None
    assert result.voltage_ac_v == Decimal(250)


def test_function_rating_prefers_the_template_and_hides_the_parts_fields(full: Model) -> None:
    """The coil's template rating wins whole: the part's DC voltage does not show through."""
    result = function_rating(full, _COIL)
    assert result == _AC
    assert result is not None
    assert result.voltage_dc_v is None


def test_function_rating_falls_back_to_the_part_without_a_template_facet(
    without_template_rating: Model, full: Model
) -> None:
    """The same function reads the part's rating once the template's facet is gone."""
    assert function_rating(full, _COIL) == _AC
    assert function_rating(without_template_rating, _COIL) == _PART_ONLY


def test_a_function_whose_template_has_no_facet_reads_the_parts_rating(full: Model) -> None:
    """The contact's template carries no `RatingFacet`, so the relay part's rating applies."""
    assert function_rating(full, _CONTACT) == _PART_ONLY


def test_a_function_with_no_template_reads_its_items_part(full: Model) -> None:
    """No template: the part comes from the function's item."""
    assert function_rating(full, _BARE) == _PART_ONLY


def test_a_function_with_neither_rating_or_no_part_is_none() -> None:
    """A part with no rating, an item with no part and an unknown id all give `None`."""
    model = _model(*_CONTACTS)
    assert function_rating(model, _COIL) is None
    assert function_rating(model, _CONTACT) is None
    assert function_rating(model, _BARE) is None
    assert function_rating(model, _HOUSING_J1) is None
    assert function_rating(model, _UNKNOWN) is None


def test_function_operating_is_per_template_with_no_fallback(full: Model) -> None:
    """Present on the coil, absent on a contact, a template-less function and an unknown id."""
    assert function_operating(full, _COIL) == _OPERATING
    assert function_operating(full, _CONTACT) is None
    assert function_operating(full, _BARE) is None
    assert function_operating(full, _UNKNOWN) is None


def test_part_rating_reads_a_part_that_has_no_function(full: Model) -> None:
    """A cable has no function; its own rating is still read. An unrated part gives `None`."""
    assert part_rating(full, _CABLE.id) == _DC
    assert part_rating(full, _RELAY) == _PART_ONLY
    assert part_rating(_model(), _RELAY) is None
    assert part_rating(full, make_id(Part, ("nowhere",))) is None


def test_the_index_is_built_once_per_digest(full: Model, without_template_rating: Model) -> None:
    """Many reads of one model build once; a model of another digest builds its own."""
    readers._index.cache_clear()
    for _ in range(3):
        for function in (_COIL, _CONTACT, _BARE, _HOUSING_J1, _UNKNOWN):
            function_rating(full, function)
            function_operating(full, function)
        part_rating(full, _RELAY)
    assert readers._index.builds == 1
    assert function_rating(without_template_rating, _COIL) == _PART_ONLY
    assert function_rating(full, _COIL) == _AC
    assert readers._index.builds == 2
    assert full.digest != without_template_rating.digest


@pytest.mark.parametrize(
    "name", ["Rating", "Operating", "function_rating", "function_operating", "part_rating"]
)
def test_derive_exports_the_read_names_as_the_vocab_objects(name: str) -> None:
    """The consumer read surface lists each name and re-exports the vocab object itself."""
    assert name in derive.__all__
    assert getattr(derive, name) is getattr(vocab, name)
