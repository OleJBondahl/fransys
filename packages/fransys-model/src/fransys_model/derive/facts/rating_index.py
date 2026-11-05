"""The one index of the rating facets of a model digest, and a function's breaking block.

Decisions model-0079 and model-0381. Built by a single pass over `facets_of` for each digest and cached on it
(`digest_cached`); below `roles`, which reads `function_block`, so `function_ratings` can read the roles.
"""

import dataclasses
lazy from decimal import Decimal

from fransys_model.derive.facts.children import children_index
from fransys_model.derive.facts.figures import figure, minimum_breaking
from fransys_model.elecdef import Current, Unit
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab.facets.rating import (
    BlockFacet,
    OperatingFacet,
    PartRatingFacet,
    RatingFacet,
)
from fransys_model.vocab.tables import facets_of, function_templates, functions, items
lazy from fransys_model.elecdef import Block, Rating
lazy from fransys_model.vocab.core import Function, Item
lazy from fransys_model.vocab.operating import Operating
lazy from fransys_model.vocab.templates import FunctionTemplate, Part


@dataclasses.dataclass(frozen=True, slots=True)
class _Index:
    """The facet kinds of one model digest, each by its subject's id."""

    template_ratings: frozendict[Id[FunctionTemplate], Rating]
    part_ratings: frozendict[Id[Part], Rating]
    blocks: frozendict[Id[FunctionTemplate], Block]
    operating: frozendict[Id[FunctionTemplate], Operating]
    link_of: frozendict[Id[Item], tuple[Rating, Block | None]]


def _link_rank(link: tuple[Id[Item], Rating, Block | None]) -> tuple[bool, Decimal, Id[Item]]:
    item, rating, block = link
    return (minimum_breaking(block) is None, max(figure(rating.current, c, Unit.A) or Decimal(0) for c in Current), item)


def _fitted_by_holder(
    model: Model, part_ratings: dict[Id[Part], Rating], part_blocks: dict[Id[Part], Block]
) -> dict[Id[Item], tuple[Rating, Block | None]]:
    """The fuse link of each holder item (model-0151): its rating and block, full-range then highest current.

    A link is a child item with a part rating and no function; the item id breaks a tie.
    """
    with_function = {record.item for record in functions(model).values()}
    found: dict[Id[Item], list[tuple[Id[Item], Rating, Block | None]]] = {}
    for holder, children in children_index(model).items():
        for child in children:
            part = items(model)[child].part
            rating = None if part is None else part_ratings.get(part)
            if rating is not None and child not in with_function:
                found.setdefault(holder, []).append((child, rating, part_blocks.get(part)))
    return {holder: max(links, key=_link_rank)[1:] for holder, links in found.items()}


@digest_cached(DIGEST_CACHE_SIZE)
def rating_index(model: Model) -> _Index:
    part_ratings = {facet.subject: facet.rating for facet in facets_of(model, PartRatingFacet).values()}
    blocks = {facet.subject: facet.block for facet in facets_of(model, BlockFacet).values()}
    part_blocks = {template.part: blocks[template.id] for template in function_templates(model).values() if template.id in blocks}
    return _Index(
        template_ratings=frozendict({facet.subject: facet.rating for facet in facets_of(model, RatingFacet).values()}),
        part_ratings=frozendict(part_ratings),
        blocks=frozendict(blocks),
        link_of=frozendict(_fitted_by_holder(model, part_ratings, part_blocks)),
        operating=frozendict({facet.subject: facet.operating for facet in facets_of(model, OperatingFacet).values()}),
    )


def function_block(model: Model, function: Id[Function]) -> Block | None:
    """The elecdef block of `function`'s template that states breaking figures; `None` for none."""
    record = functions(model).get(function)
    return None if record is None or record.template is None else rating_index(model).blocks.get(record.template)
