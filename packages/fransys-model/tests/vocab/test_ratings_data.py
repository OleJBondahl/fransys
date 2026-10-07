"""RATINGS-1 step 2, part 1: `Rating`, `Operating` and the three facets that hold them.

Storage only (decision model-0079): the types, the kinds and their schema rules. No check
reads them here.
"""

import dataclasses
from decimal import Decimal
from types import UnionType
from typing import Any, get_args

import pytest
from examples import core_model, relay_part_bundle

from fransys_model.kernel import (
    FreezeError,
    Id,
    Model,
    Origin,
    RefError,
    SchemaError,
    dumps,
    freeze,
    from_data,
    loads,
    lookup_kind,
    make_id,
    merge,
    namespace_of,
    to_data,
)
from fransys_model.kernel.schema import annotations_of, resolve_target
from fransys_model.vocab import (
    BreakingPoint,
    Operating,
    OperatingFacet,
    PartRatingFacet,
    Rating,
    RatingFacet,
)
from fransys_model.vocab.tables import facets_of
from fransys_model.vocab.templates import FunctionTemplate, Part

_ORIGIN = Origin(file="test_ratings_data.py", line=1, note="fixture")
_COIL = make_id(FunctionTemplate, ("examples", "relay", "fn", "coil"))
_CONTACT = make_id(FunctionTemplate, ("examples", "relay", "fn", "no_1"))
_PART = relay_part_bundle().part.id
_RATING = Rating(voltage_ac_v=Decimal(250), voltage_dc_v=None, current_ac_a=Decimal("0.5"))
_OPERATING = Operating(
    nominal_voltage_v=Decimal(24), min_voltage_v=Decimal(18), capacity_ah=Decimal("7.2")
)

# (kind, subject class, value field, value class)
_ROWS = [
    ("facet.rating", FunctionTemplate, "rating", Rating),
    ("facet.part_rating", Part, "rating", Rating),
    ("facet.operating", FunctionTemplate, "operating", Operating),
]
_IDS = [row[0] for row in _ROWS]


def _model(*records: Any) -> Model:
    draft = merge(core_model())
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def _rating(subject: Any = _COIL, tag: str = "a", rating: Any = _RATING) -> RatingFacet:
    key = ("ratings", "rating", tag)
    return RatingFacet(id=make_id(RatingFacet, key), key=key, subject=subject, rating=rating)


def _part_rating(subject: Any = _PART, tag: str = "a") -> PartRatingFacet:
    key = ("ratings", "part_rating", tag)
    return PartRatingFacet(
        id=make_id(PartRatingFacet, key), key=key, subject=subject, rating=_RATING
    )


def _operating(subject: Any = _COIL, tag: str = "a", operating: Any = _OPERATING) -> OperatingFacet:
    key = ("ratings", "operating", tag)
    return OperatingFacet(
        id=make_id(OperatingFacet, key), key=key, subject=subject, operating=operating
    )


@pytest.mark.parametrize(("kind", "subject", "field", "value_cls"), _ROWS, ids=_IDS)
def test_the_kind_is_registered_in_the_facet_namespace_and_unique_per_subject(
    kind: str, subject: Any, field: str, value_cls: type
) -> None:
    """Kind, namespace, `unique=True` on `subject`, the subject's type and the value field."""
    cls: Any = lookup_kind(kind)
    assert namespace_of(kind) == "facet"
    assert (cls.__unique__, cls.__subject__) == (True, "subject")
    annotations = annotations_of(cls)
    (target,) = get_args(annotations["subject"])
    assert resolve_target(target, cls, "subject") == subject.__kind__
    assert annotations[field] is value_cls
    assert list(annotations) == ["id", "key", "subject", field, "ext"]


def test_the_value_types_hold_only_optional_decimals() -> None:
    """Rating and Operating hold `Decimal | None` fields defaulting to `None`; points are tuples."""
    assert list(annotations_of(Rating)) == [
        "voltage_ac_v",
        "voltage_dc_v",
        "current_ac_a",
        "current_dc_a",
        "min_breaking_current_a",
        "power_loss_w",
        "breaking_ac",
        "breaking_dc",
    ]
    assert list(annotations_of(Operating)) == [
        "voltage_ac_v",
        "voltage_dc_v",
        "nominal_voltage_v",
        "max_voltage_v",
        "min_voltage_v",
        "capacity_ah",
        "max_current_ac_a",
        "max_current_dc_a",
        "resistance_ohm",
        "nominal_power_w",
        "nominal_current_a",
        "fault_current_ac_a",
        "fault_current_dc_a",
        "fault_time_constant_ms",
    ]
    points = {"breaking_ac", "breaking_dc"}
    for cls in (Rating, Operating):
        for name, annotation in annotations_of(cls).items():
            if name in points:
                assert get_args(annotation)[0] is BreakingPoint, name
                continue
            assert isinstance(annotation, UnionType), name
            assert set(get_args(annotation)) == {Decimal, type(None)}, name
        assert all(v in (None, ()) for v in dataclasses.asdict(cls()).values())


def test_a_model_with_all_three_facets_survives_both_codecs_with_an_equal_digest() -> None:
    """`None` stays `None` and the `Decimal`s keep their exact value through text and data forms."""
    model = _model(_rating(), _part_rating(), _operating())
    for again in (loads(dumps(model)), from_data(to_data(model))):
        assert again == model
        assert again.digest == model.digest
        (rating,) = facets_of(again, RatingFacet).values()
        assert rating.rating == _RATING
        assert rating.rating.voltage_dc_v is None
        assert rating.rating.current_ac_a == Decimal("0.5")
        (operating,) = facets_of(again, OperatingFacet).values()
        assert operating.operating.capacity_ah == Decimal("7.2")
        assert operating.operating.max_voltage_v is None


def test_the_current_fields_survive_both_codecs_with_an_equal_digest() -> None:
    """`min_breaking_current_a` and the two max currents keep their exact `Decimal` value."""
    rating = Rating(current_dc_a=Decimal(400), min_breaking_current_a=Decimal(4000))
    operating = Operating(max_current_ac_a=Decimal("63.5"), max_current_dc_a=Decimal(186))
    model = _model(_rating(rating=rating), _part_rating(), _operating(operating=operating))
    for again in (loads(dumps(model)), from_data(to_data(model))):
        assert again == model
        assert again.digest == model.digest
        (facet,) = facets_of(again, RatingFacet).values()
        assert facet.rating == rating
        assert facet.rating.min_breaking_current_a == Decimal(4000)
        (facet_op,) = facets_of(again, OperatingFacet).values()
        assert facet_op.operating == operating
        assert facet_op.operating.max_current_ac_a == Decimal("63.5")
        assert facet_op.operating.max_current_dc_a == Decimal(186)


@pytest.mark.parametrize("make", [_rating, _part_rating, _operating], ids=_IDS)
def test_a_second_facet_of_one_kind_on_one_subject_is_refused(make: Any) -> None:
    """`unique=True`: `freeze` raises one `SchemaError` naming the later record."""
    first, second = make(tag="a"), make(tag="b")
    with pytest.raises(FreezeError) as excinfo:
        _model(first, second)
    (error,) = excinfo.value.errors
    assert isinstance(error, SchemaError)
    assert error.record_id == max(first.id, second.id)
    assert "per subject" in str(error)


def test_a_rating_and_an_operating_facet_share_one_template() -> None:
    """Different kinds do not count against each other; two templates of one kind are fine too."""
    model = _model(_rating(_COIL), _operating(_COIL), _rating(_CONTACT, tag="b"))
    assert len(facets_of(model, RatingFacet)) == 2
    assert len(facets_of(model, OperatingFacet)) == 1


def test_a_float_in_a_rating_field_is_one_schema_error() -> None:
    """The kernel refuses a `float` for a `Decimal` field of a nested value, naming the path."""
    with pytest.raises(FreezeError) as excinfo:
        _model(_rating(rating=Rating(voltage_ac_v=250.0)))  # ty: ignore[invalid-argument-type] -- a float for a nested `Decimal` field, testing the kernel's own schema check on it
    (error,) = excinfo.value.errors
    assert isinstance(error, SchemaError)
    assert "RatingFacet.rating.voltage_ac_v: expected Decimal, got float" in str(error)


def test_a_float_in_an_operating_field_is_one_schema_error() -> None:
    """Same for the other value type: `capacity_ah` as a `float`."""
    with pytest.raises(FreezeError) as excinfo:
        _model(_operating(operating=Operating(capacity_ah=7.2)))  # ty: ignore[invalid-argument-type] -- same check on `Operating`'s own `Decimal` field, `capacity_ah`
    (error,) = excinfo.value.errors
    assert "OperatingFacet.operating.capacity_ah: expected Decimal, got float" in str(error)


@pytest.mark.parametrize(
    "bad", [{"voltage_ac_v": Decimal(1)}, None, "250"], ids=["dict", "none", "str"]
)
def test_a_value_field_that_is_not_the_value_type_is_refused(bad: Any) -> None:
    """A `dict` for `rating`, a missing one and a string are each a `FreezeError` naming it."""
    with pytest.raises(FreezeError) as excinfo:
        _model(_rating(rating=bad))
    assert "RatingFacet.rating" in str(excinfo.value.errors[0])


def test_a_rating_cannot_be_assigned_to() -> None:
    """Frozen: a field assignment raises `FrozenInstanceError`, on both value types."""
    with pytest.raises(dataclasses.FrozenInstanceError):
        _RATING.voltage_ac_v = Decimal(1)  # ty: ignore[invalid-assignment] -- the assignment `FrozenInstanceError` this test asserts on, on the `Rating` value type
    with pytest.raises(dataclasses.FrozenInstanceError):
        _OPERATING.capacity_ah = Decimal(1)  # ty: ignore[invalid-assignment] -- same assignment refusal, on the `Operating` value type


@pytest.mark.parametrize(
    ("make", "missing"),
    [
        (_rating, make_id(FunctionTemplate, ("nowhere",))),
        (_part_rating, make_id(Part, ("nowhere",))),
        (_operating, make_id(FunctionTemplate, ("nowhere",))),
    ],
    ids=_IDS,
)
def test_a_dangling_subject_is_refused_at_freeze(make: Any, missing: Id[Any]) -> None:
    """A subject with no record is a `RefError` on `subject`, like any facet."""
    with pytest.raises(FreezeError) as excinfo:
        _model(make(missing))
    (error,) = excinfo.value.errors
    assert isinstance(error, RefError)
    assert (error.field, error.target) == ("subject", missing)
