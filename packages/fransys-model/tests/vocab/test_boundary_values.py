"""RATINGS-1 Q5, model side: `BoundaryValuesFacet` and its two readers (decision model-0081).

A unit's boundary values are a facet on its `Boundary`, never fields on a core kind, so a model
without the facet keeps its digest. The readers answer the authored value only: no fallback to the
function's part, which `function_rating` reads on its own.
"""

from decimal import Decimal
from types import NoneType
from typing import Any, get_args

import pytest
from plant import Plant

from fransys_model import derive, vocab
from fransys_model.kernel import (
    FreezeError,
    Model,
    RefError,
    SchemaError,
    dumps,
    from_data,
    loads,
    lookup_kind,
    make_id,
    namespace_of,
    to_data,
)
from fransys_model.kernel.schema import annotations_of, resolve_target
from fransys_model.vocab import (
    BoundaryValuesFacet,
    Operating,
    PartRatingFacet,
    Rating,
    boundary_operating,
    boundary_rating,
    function_rating,
)
from fransys_model.vocab.core import Unit
from fransys_model.vocab.tables import facets_of
from fransys_model.vocab.units import Boundary

_B1 = make_id(Boundary, ("b1",))
_B2 = make_id(Boundary, ("b2",))
_RATING = Rating(voltage_ac_v=Decimal(250), current_ac_a=Decimal("0.5"))
_OTHER_RATING = Rating(voltage_dc_v=Decimal(60))
_OPERATING = Operating(
    nominal_voltage_v=Decimal(24), min_voltage_v=Decimal(18), max_voltage_v=Decimal(30)
)


def _plant() -> Plant:
    """Two units whose interface is the same connector function: boundaries `b1` and `b2`."""
    plant = Plant()
    board = plant.unit("board")
    cabinet = plant.unit("cabinet")
    plant.pin("x1", "conn", "1")
    function = Plant.function_id("x1", "conn")
    plant.boundary(board, function, key="b1")
    plant.boundary(cabinet, function, key="b2")
    return plant


def _model(*records: Any) -> Model:
    plant = _plant()
    plant.add(*records)
    return plant.model()


def _facet(
    subject: Any = _B1,
    tag: str = "a",
    rating: Rating | None = None,
    operating: Operating | None = None,
) -> BoundaryValuesFacet:
    key = ("boundary_values", tag)
    return BoundaryValuesFacet(
        id=make_id(BoundaryValuesFacet, key),
        key=key,
        subject=subject,
        rating=rating,
        operating=operating,
    )


def test_the_kind_is_registered_in_the_facet_namespace_and_unique_per_subject() -> None:
    """Kind, namespace, `unique=True` on `subject`, a `Boundary` subject, optional value fields."""
    cls: Any = lookup_kind("facet.boundary_values")
    assert cls is BoundaryValuesFacet
    assert namespace_of("facet.boundary_values") == "facet"
    assert (cls.__unique__, cls.__subject__) == (True, "subject")
    annotations = annotations_of(cls)
    assert list(annotations) == ["id", "key", "subject", "rating", "operating", "ext"]
    (target,) = get_args(annotations["subject"])
    boundary: Any = Boundary
    assert resolve_target(target, cls, "subject") == boundary.__kind__
    assert set(get_args(annotations["rating"])) == {Rating, NoneType}
    assert set(get_args(annotations["operating"])) == {Operating, NoneType}


@pytest.mark.parametrize(
    ("rating", "operating"),
    [(_RATING, None), (None, _OPERATING), (_RATING, _OPERATING)],
    ids=["rating-only", "operating-only", "both"],
)
def test_a_facet_with_a_rating_or_an_operating_or_both_freezes_and_is_read_back(
    rating: Rating | None, operating: Operating | None
) -> None:
    """Either value may be absent; `facets_of` finds the facet on its `Boundary`."""
    facet = _facet(rating=rating, operating=operating)
    assert facets_of(_model(facet), BoundaryValuesFacet) == {facet.id: facet}


def test_a_facet_with_neither_a_rating_nor_an_operating_is_refused() -> None:
    """Both `None` says nothing: `SchemaError` at construction, naming the kind and the record."""
    key = ("boundary_values", "empty")
    facet_id = make_id(BoundaryValuesFacet, key)
    with pytest.raises(SchemaError) as excinfo:
        BoundaryValuesFacet(id=facet_id, key=key, subject=_B1)
    assert excinfo.value.record_id == facet_id
    assert excinfo.value.kind == "facet.boundary_values"
    assert "neither a rating nor an operating" in str(excinfo.value)


def test_a_facet_with_neither_value_and_a_wrong_typed_id_is_still_refused() -> None:
    """The refusal does not depend on the id: a non-`Id` gives `record_id=None`, not a crash."""
    bad_id: Any = "not-an-id"
    with pytest.raises(SchemaError) as excinfo:
        BoundaryValuesFacet(id=bad_id, key=("k",), subject=_B1)
    assert excinfo.value.record_id is None


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"rating": {"voltage_ac_v": Decimal(1)}}, "rating"),
        ({"operating": "24"}, "operating"),
        ({"rating": _RATING, "operating": 24}, "operating"),
    ],
    ids=["rating-dict", "operating-str", "operating-int-beside-rating"],
)
def test_a_wrong_typed_value_is_left_for_freeze_to_report_once(
    changes: dict[str, Any], field: str
) -> None:
    """A wrong type is one `FreezeError` naming the field; only both-`None` is refused earlier."""
    facet = _facet(**changes)
    with pytest.raises(FreezeError) as excinfo:
        _model(facet)
    (error,) = excinfo.value.errors
    assert f"BoundaryValuesFacet.{field}" in str(error)


def test_a_model_with_the_facet_survives_both_codecs_with_an_equal_digest() -> None:
    """`None` stays `None` and the `Decimal`s keep their exact value through text and data forms."""
    rating_only = _facet(_B1, "a", rating=_RATING)
    operating_only = _facet(_B2, "b", operating=_OPERATING)
    model = _model(rating_only, operating_only)
    for again in (loads(dumps(model)), from_data(to_data(model))):
        assert again == model
        assert again.digest == model.digest
        facets = facets_of(again, BoundaryValuesFacet)
        assert facets[rating_only.id].rating == _RATING
        assert facets[rating_only.id].operating is None
        assert facets[operating_only.id].rating is None
        assert facets[operating_only.id].operating == _OPERATING


def test_two_facets_on_one_boundary_are_refused() -> None:
    """`unique=True`: `freeze` raises one `SchemaError` naming the later record."""
    first = _facet(tag="a", rating=_RATING)
    second = _facet(tag="b", operating=_OPERATING)
    with pytest.raises(FreezeError) as excinfo:
        _model(first, second)
    (error,) = excinfo.value.errors
    assert isinstance(error, SchemaError)
    assert error.record_id == max(first.id, second.id)
    assert "per subject" in str(error)


def test_two_boundaries_of_one_function_each_carry_their_own_facet() -> None:
    """The subject is the `Boundary`, not the function: the same function states two values."""
    model = _model(_facet(_B1, "a", rating=_RATING), _facet(_B2, "b", rating=_OTHER_RATING))
    assert boundary_rating(model, _B1) == _RATING
    assert boundary_rating(model, _B2) == _OTHER_RATING


@pytest.mark.parametrize("kind", ["unit", "function"])
def test_a_subject_that_is_not_a_boundary_is_refused_at_freeze(kind: str) -> None:
    """A unit or a function id exists in the model but is not a `Boundary`: a `RefError`."""
    wrong = {
        "unit": make_id(Unit, ("board",)),
        "function": Plant.function_id("x1", "conn"),
    }[kind]
    with pytest.raises(FreezeError) as excinfo:
        _model(_facet(wrong, rating=_RATING))
    (error,) = excinfo.value.errors
    assert isinstance(error, RefError)
    assert (error.field, error.target) == ("subject", wrong)


def test_a_dangling_boundary_subject_is_refused_at_freeze() -> None:
    """A `Boundary` id with no record is a `RefError` on `subject`."""
    missing = make_id(Boundary, ("nowhere",))
    with pytest.raises(FreezeError) as excinfo:
        _model(_facet(missing, rating=_RATING))
    (error,) = excinfo.value.errors
    assert isinstance(error, RefError)
    assert (error.field, error.target) == ("subject", missing)


def test_the_readers_return_the_authored_values() -> None:
    """A rating-only, an operating-only and a both facet each read back exactly what it holds."""
    model = _model(
        _facet(_B1, "a", rating=_RATING),
        _facet(_B2, "b", rating=_OTHER_RATING, operating=_OPERATING),
    )
    assert boundary_rating(model, _B1) == _RATING
    assert boundary_operating(model, _B1) is None
    assert boundary_rating(model, _B2) == _OTHER_RATING
    assert boundary_operating(model, _B2) == _OPERATING


def test_the_readers_return_none_without_a_facet_or_for_an_unknown_boundary() -> None:
    """No facet, an unset field and an id that is no boundary all give `None`."""
    model = _model(_facet(_B1, "a", operating=_OPERATING))
    assert boundary_rating(model, _B1) is None
    assert boundary_rating(model, _B2) is None
    assert boundary_operating(model, _B2) is None
    nowhere = make_id(Boundary, ("nowhere",))
    assert boundary_rating(model, nowhere) is None
    assert boundary_operating(model, nowhere) is None
    assert boundary_rating(_model(), _B1) is None
    assert boundary_operating(_model(), _B1) is None


def test_the_readers_do_not_fall_back_to_the_functions_part_rating() -> None:
    """The function's part rating is `function_rating`'s source; the boundary reads only its own."""
    plant = _plant()
    part = plant.part("X")
    plant.add(
        PartRatingFacet(
            id=make_id(PartRatingFacet, ("part-rating",)),
            key=("part-rating",),
            subject=part,
            rating=_RATING,
        )
    )
    function = plant.function(plant.item("k1", part=part), "coil")
    plant.boundary(make_id(Unit, ("board",)), function, key="b3")
    model = plant.model()
    b3 = make_id(Boundary, ("b3",))
    assert function_rating(model, function) == _RATING
    assert boundary_rating(model, b3) is None
    assert boundary_operating(model, b3) is None


def test_derive_and_vocab_export_the_facet_and_the_readers() -> None:
    """The consumer read surface lists both readers and re-exports the vocab objects themselves."""
    for name in ("boundary_rating", "boundary_operating"):
        assert name in derive.__all__
        assert getattr(derive, name) is getattr(vocab, name)
    assert "BoundaryValuesFacet" in vocab.__all__


def test_a_model_without_the_facet_holds_no_rows_of_its_kind() -> None:
    """A model that never uses the kind has no rows of it (its digest is the goldens' concern)."""
    assert facets_of(_model(), BoundaryValuesFacet) == {}
