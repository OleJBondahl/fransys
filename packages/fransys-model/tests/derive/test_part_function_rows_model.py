"""`part_function_rows`: a row per template, one per function-less part, the rating by fallback."""

from decimal import Decimal

from current_plant import rate
from plant import Plant

from fransys_model.derive import part_function_rows
from fransys_model.kernel import make_id
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.facets.rating import PartRatingFacet, RatingFacet
from fransys_model.vocab.ratings import Rating

_PART = Rating(current_dc_a=Decimal(10))
_OWN = Rating(current_dc_a=Decimal(2))


def _relay(plant: Plant, *, own: Rating | None = None):
    part, template, _, _ = plant.relay_part()
    if own is not None:
        key = ("relay", "part-rating")
        plant.add(
            PartRatingFacet(id=make_id(PartRatingFacet, key), key=key, subject=part.id, rating=own)
        )
    return part, template


def test_a_template_with_no_rating_takes_its_parts() -> None:
    """The fallback: the template states none, so the row carries the part's rating."""
    plant = Plant()
    _relay(plant, own=_PART)
    (row,) = part_function_rows(plant.model())
    assert (row.mpn, row.name, row.kind, row.rating) == (
        "EXAMPLE-1",
        "fn",
        FunctionKind.GENERIC,
        _PART,
    )


def test_a_template_rating_replaces_the_parts_whole() -> None:
    """The positive pair of the fallback test: a stated template rating wins."""
    plant = Plant()
    _part, template = _relay(plant, own=_PART)
    key = ("relay", "fn", "rating")
    plant.add(RatingFacet(id=make_id(RatingFacet, key), key=key, subject=template.id, rating=_OWN))
    (row,) = part_function_rows(plant.model())
    assert row.rating == _OWN
    assert row.template == template.id


def test_a_function_less_part_has_one_row_with_its_own_rating() -> None:
    """A fuse link has no template: one row, no template, no kind, the part's rating."""
    plant = Plant()
    part = rate(plant, "L", "4")
    (row,) = part_function_rows(plant.model())
    assert (row.part, row.template, row.name, row.kind) == (part, None, "", None)
    assert row.rating == Rating(current_dc_a=Decimal(4))
