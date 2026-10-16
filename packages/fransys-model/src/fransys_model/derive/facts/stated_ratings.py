"""The ratings a function is checked against, each with its source (model-0079, model-0151).

Split from `function_ratings` so a protection's fitted link can read `function_role`.
"""

import dataclasses
from typing import TYPE_CHECKING

from fransys_model.derive.facts.function_ratings import (
    boundary_rating,
    function_operatings,
    function_rating,
    rating_index,
)
from fransys_model.derive.facts.roles import function_role
from fransys_model.derive.facts.unit_index import boundary_unit
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import functions, units
lazy from fransys_model.vocab.ratings import Rating

if TYPE_CHECKING:
    from fransys_model.derive.facts.function_ratings import FunctionOperating
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function, Unit


@dataclasses.dataclass(frozen=True, slots=True)
class FunctionRating:
    """One rating a function is checked against, with its source.

    `unit` is `None` for the part or template rating, else the unit whose boundary rating it is.
    """

    rating: Rating
    unit: Id[Unit] | None


def rating_source_label(model: Model, source: FunctionRating | FunctionOperating) -> str:
    """The text for where a stated rating comes from: the part or template, or a unit's boundary."""
    unit = source.unit
    if unit is None:
        return "part or template rating"
    return f"boundary rating of {ref(units(model)[unit])}"


def fitted_link_rating(model: Model, function: Id[Function]) -> Rating | None:
    """The rating of the fuse link fitted in a protection `function`'s holder (model-0151).

    The holder item's highest-rated link; `None` for no link or a function other than protection.
    """
    record = functions(model).get(function)
    if record is None or not function_role(model, function).protects:
        return None
    return rating_index(model).link_of.get(record.item)


def function_ratings(model: Model, function: Id[Function]) -> tuple[FunctionRating, ...]:
    """Every rating `function` is checked against in `model`, each with its source.

    The part or template rating, then a protection function's highest fuse link (model-0151), then
    one per `Boundary` in id order stating one. Each boundary has no fallback.
    """
    if function not in functions(model):
        return ()
    found: list[FunctionRating] = []
    own = function_rating(model, function)
    if own is not None:
        found.append(FunctionRating(own, None))
    link = fitted_link_rating(model, function)
    if link is not None:
        found.append(FunctionRating(link, None))
    for boundary in rating_index(model).boundaries_of.get(function, ()):
        rating = boundary_rating(model, boundary.id)
        if rating is not None:
            found.append(FunctionRating(rating, boundary_unit(model, boundary.id)))
    return tuple(found)


def states_current(model: Model, function: Id[Function]) -> bool:
    """Whether `function` states any current: a rating's current, or a source's continuous limit.

    The one place of "a rated current path": any `function_ratings` or `function_operatings` source
    with an AC or DC current or continuous limit set. Voltages alone do not.
    """
    return any(
        r.rating.current_ac_a is not None or r.rating.current_dc_a is not None
        for r in function_ratings(model, function)
    ) or any(
        o.operating.max_current_ac_a is not None or o.operating.max_current_dc_a is not None
        for o in function_operatings(model, function)
    )
