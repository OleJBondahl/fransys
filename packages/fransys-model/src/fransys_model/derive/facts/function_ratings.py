"""Typed readers of the rating facets: what a function or a part is rated for.

Decisions model-0079 and model-0381. One index of the facet kinds is built by a single
pass over `facets_of` for each model digest and cached on it (`digest_cached`), so the first call
costs O(F) and every later call O(1). A function's rating is its template's, else its part's.
"""

import dataclasses
from typing import Final

from fransys_model.derive.facts.rating_index import rating_index
from fransys_model.vocab.tables import function_templates, functions, items
lazy from fransys_model.derive.facts.roles import function_role
lazy from fransys_model.elecdef import Block, Rating
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function
lazy from fransys_model.vocab.operating import Operating
lazy from fransys_model.vocab.templates import FunctionTemplate, Part


def function_rating(model: Model, function: Id[Function]) -> Rating | None:
    """The rating of `function`: its template's, else its part's; `None` when neither has one.

    The part is the template's part when the function has a template, else its item's part. A
    template rating replaces the part's whole. Use this on a built model; before a build use d.rating.
    """
    record = functions(model).get(function)
    if record is None:
        return None
    index = rating_index(model)
    own = None if record.template is None else index.template_ratings.get(record.template)
    part = items(model)[record.item].part if record.template is None else function_templates(model)[record.template].part
    return own if own is not None else None if part is None else index.part_ratings.get(part)


RATING_SOURCE_LABEL: Final = "part or template rating"


@dataclasses.dataclass(frozen=True, slots=True)
class FunctionOperating:
    """One operating envelope a function states."""

    operating: Operating


@dataclasses.dataclass(frozen=True, slots=True)
class FunctionRating:
    """One rating a function is checked against: the part or template rating, or the fitted link's."""

    rating: Rating


def function_operating(model: Model, function: Id[Function]) -> Operating | None:
    """The operating envelope of `function`'s template; `None` with no template or no facet (no part fallback)."""
    record = functions(model).get(function)
    return None if record is None or record.template is None else rating_index(model).operating.get(record.template)


def template_rating(model: Model, template: Id[FunctionTemplate]) -> Rating | None:
    """The rating a function template states itself, with no fallback to its part."""
    return rating_index(model).template_ratings.get(template)


def part_rating(model: Model, part: Id[Part]) -> Rating | None:
    """The rating of `part` itself, for a part with no function to ask about (a fuse link)."""
    return rating_index(model).part_ratings.get(part)


def function_operatings(model: Model, function: Id[Function]) -> tuple[FunctionOperating, ...]:
    """Every operating envelope `function` states: its template's."""
    return () if (o := function_operating(model, function)) is None else (FunctionOperating(o),)


def _fitted_link(model: Model, function: Id[Function]) -> tuple[Rating, Block | None] | None:
    record = functions(model).get(function)
    if record is None or not function_role(model, function).protects:
        return None
    return rating_index(model).link_of.get(record.item)


def fitted_link_rating(model: Model, function: Id[Function]) -> Rating | None:
    """The rating of the fuse link fitted in a protection `function`'s holder (model-0151), else `None`."""
    link = _fitted_link(model, function)
    return None if link is None else link[0]


def fitted_link_block(model: Model, function: Id[Function]) -> Block | None:
    """The block of the fitted fuse link (its part's template `BlockFacet`); `None` for none or no link."""
    link = _fitted_link(model, function)
    return None if link is None else link[1]


def function_ratings(model: Model, function: Id[Function]) -> tuple[FunctionRating, ...]:
    """Every rating `function` is checked against: part or template, then the fitted link."""
    if function not in functions(model):
        return ()
    return tuple(FunctionRating(r) for r in (function_rating(model, function), fitted_link_rating(model, function)) if r is not None)


def states_current(model: Model, function: Id[Function]) -> bool:
    """Whether `function` states any current: a rating's current, or a source's continuous limit."""
    return any(r.rating.current for r in function_ratings(model, function)) or any(
        o.operating.max_current for o in function_operatings(model, function)
    )
