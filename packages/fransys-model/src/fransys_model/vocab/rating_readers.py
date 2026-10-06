"""Typed readers of the rating facets: what a function, a part or a boundary is rated for.

Decisions model-0079 and model-0081. A caller never spells a facet kind or a subject id. One
index of the four facet kinds (`subject id -> value`, or the facet for a boundary) is built by a
single pass over `facets_of` for each model digest and cached on it (`digest_cached`, the last
`DIGEST_CACHE_SIZE`, like `port_rails`), so the first call costs O(F) for F facets and every
later call O(1); a consumer reading every function is linear overall. The fallback rule itself
lives in `ratings.effective_rating`.
"""

import dataclasses
from typing import TYPE_CHECKING

from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached

from .facets.rating import BoundaryValuesFacet, OperatingFacet, PartRatingFacet, RatingFacet
from .ratings import Operating, Rating, effective_rating
from .tables import boundaries, facets_of, function_templates, functions, items
lazy from .core import Function
lazy from .templates import Part
lazy from .units import Boundary

if TYPE_CHECKING:
    from .core import Unit
    from .templates import FunctionTemplate


@dataclasses.dataclass(frozen=True, slots=True)
class FunctionRating:
    """One rating a function is checked against, with its source.

    `unit` is `None` for the part or template rating, else the unit whose boundary rating it is.
    """

    rating: Rating
    unit: Id[Unit] | None


@dataclasses.dataclass(frozen=True, slots=True)
class _Index:
    """The four facet kinds of one model digest, each by its subject's id, and the boundaries."""

    template_ratings: frozendict[Id[FunctionTemplate], Rating]
    part_ratings: frozendict[Id[Part], Rating]
    operating: frozendict[Id[FunctionTemplate], Operating]
    boundary_values: frozendict[Id[Boundary], BoundaryValuesFacet]
    boundaries_of: frozendict[Id[Function], tuple[Boundary, ...]]


@digest_cached(DIGEST_CACHE_SIZE)
def _index(model: Model) -> _Index:
    of_function: dict[Id[Function], list[Boundary]] = {}
    for boundary in sorted(boundaries(model).values(), key=lambda b: b.id):
        of_function.setdefault(boundary.function, []).append(boundary)
    return _Index(
        template_ratings=frozendict(
            {facet.subject: facet.rating for facet in facets_of(model, RatingFacet).values()}
        ),
        part_ratings=frozendict(
            {facet.subject: facet.rating for facet in facets_of(model, PartRatingFacet).values()}
        ),
        operating=frozendict(
            {facet.subject: facet.operating for facet in facets_of(model, OperatingFacet).values()}
        ),
        boundary_values=frozendict(
            {facet.subject: facet for facet in facets_of(model, BoundaryValuesFacet).values()}
        ),
        boundaries_of=frozendict({key: tuple(found) for key, found in of_function.items()}),
    )


def function_rating(model: Model, function: Id[Function]) -> Rating | None:
    """The rating of `function`: its template's, else its part's; `None` when neither has one.

    The part is the function template's part when the function has a template, else its item's
    part. The template's `Rating` replaces the part's whole (`effective_rating`). A function
    with no template and no part, or an id that is not a function of `model`, gives `None`.

    Args:
        model: The model to read.
        function: The function whose rating is looked up.

    Returns:
        `function`'s template `Rating` when it has one, else its part's, else `None`.
    """
    record = functions(model).get(function)
    if record is None:
        return None
    index = _index(model)
    part: Id[Part] | None
    if record.template is None:
        item = items(model)[record.item]
        part = item.part
        template_rating = None
    else:
        template = function_templates(model)[record.template]
        part = template.part
        template_rating = index.template_ratings.get(record.template)
    return effective_rating(template_rating, None if part is None else index.part_ratings.get(part))


def function_ratings(model: Model, function: Id[Function]) -> tuple[FunctionRating, ...]:
    """Every rating `function` is checked against in `model`, each with its source.

    The part or template rating (`unit` is `None`), then one per `Boundary` in id order stating one.
    Each boundary is its own source, read with no fallback to the part's; an unknown id gives none.
    """
    if function not in functions(model):
        return ()
    found: list[FunctionRating] = []
    own = function_rating(model, function)
    if own is not None:
        found.append(FunctionRating(own, None))
    for boundary in _index(model).boundaries_of.get(function, ()):
        rating = boundary_rating(model, boundary.id)
        if rating is not None:
            found.append(FunctionRating(rating, boundary.unit))
    return tuple(found)


@dataclasses.dataclass(frozen=True, slots=True)
class FunctionOperating:
    """One operating envelope a function states, with its source (like `FunctionRating`).

    `unit` is `None` for the template's envelope, else the unit whose boundary states it.
    """

    operating: Operating
    unit: Id[Unit] | None


def function_operatings(model: Model, function: Id[Function]) -> tuple[FunctionOperating, ...]:
    """Every operating envelope `function` states in `model`, each with its source.

    The template's (`unit` is `None`), then one per `Boundary` in id order whose unit states one.
    Each is read on its own fields, with no fallback; an id that is not a function gives none.
    """
    if function not in functions(model):
        return ()
    found: list[FunctionOperating] = []
    own = function_operating(model, function)
    if own is not None:
        found.append(FunctionOperating(own, None))
    for boundary in _index(model).boundaries_of.get(function, ()):
        operating = boundary_operating(model, boundary.id)
        if operating is not None:
            found.append(FunctionOperating(operating, boundary.unit))
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


def function_operating(model: Model, function: Id[Function]) -> Operating | None:
    """The operating envelope of `function`'s template; `None` with no template or no facet.

    There is no fallback to the part: operating characteristics are per template.

    Args:
        model: The model to read.
        function: The function whose operating envelope is looked up.

    Returns:
        `function`'s template `Operating`, or `None` when it has no template or no facet.
    """
    record = functions(model).get(function)
    if record is None or record.template is None:
        return None
    return _index(model).operating.get(record.template)


def boundary_rating(model: Model, boundary: Id[Boundary]) -> Rating | None:
    """The rating a unit states on `boundary`; `None` with no facet or no rating in it.

    No fallback: the function's own part rating is a separate source, read through
    `function_rating`.

    Args:
        model: The model to read.
        boundary: The boundary whose stated rating is looked up.

    Returns:
        The `Rating` `boundary`'s unit states, or `None` with no facet or no rating in it.
    """
    facet = _index(model).boundary_values.get(boundary)
    return None if facet is None else facet.rating


def boundary_operating(model: Model, boundary: Id[Boundary]) -> Operating | None:
    """The operating envelope a unit states on `boundary`; `None` with no facet or none in it.

    Args:
        model: The model to read.
        boundary: The boundary whose stated operating envelope is looked up.

    Returns:
        The `Operating` `boundary`'s unit states, or `None` with no facet or none in it.
    """
    facet = _index(model).boundary_values.get(boundary)
    return None if facet is None else facet.operating


def part_rating(model: Model, part: Id[Part]) -> Rating | None:
    """The rating of `part` itself, for a part with no function to ask about (a fuse link).

    Args:
        model: The model to read.
        part: The part whose own rating is looked up.

    Returns:
        `part`'s `Rating`, or `None` when it has no rating facet or `part` is not a part of
        `model`.
    """
    return _index(model).part_ratings.get(part)
