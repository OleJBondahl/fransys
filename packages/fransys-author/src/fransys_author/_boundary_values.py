"""A `BoundaryValuesFacet` from `s.boundary(...)` (spec Q5); a non-`Decimal` is `freeze`'s.

An empty `Rating` or `Operating` says nothing, so the builder refuses it.
"""

import dataclasses
from typing import TYPE_CHECKING

from fransys_model.kernel import make_id
from fransys_model.vocab import BoundaryValuesFacet, Operating, Rating

from ._keys import scoped
from .errors import AuthorError

if TYPE_CHECKING:
    from fransys_model.kernel import AuthoringKey, Id
    from fransys_model.vocab import Boundary


def build_boundary_values(
    boundary_key: AuthoringKey,
    boundary_id: Id[Boundary],
    rating: Rating | None,
    operating: Operating | None,
) -> BoundaryValuesFacet | None:
    """The facet `boundary(...)` writes beside its `Boundary`, or `None` when no value is given."""
    _check("rating", rating, Rating)
    _check("operating", operating, Operating)
    if rating is None and operating is None:
        return None
    key = scoped(boundary_key, "boundary_values")
    return BoundaryValuesFacet(
        id=make_id(BoundaryValuesFacet, key),
        key=key,
        subject=boundary_id,
        rating=rating,
        operating=operating,
    )


def _check(argument: str, value: object, expected: type[Rating | Operating]) -> None:
    if value is None:
        return
    if not isinstance(value, expected):
        msg = f"boundary() {argument}= must be a {expected.__name__} or None, not {value!r}"
        raise AuthorError(msg)
    if all(getattr(value, f.name) is None for f in dataclasses.fields(expected)):
        msg = f"boundary() {argument}= {value!r} states no value; set at least one field"
        raise AuthorError(msg)
