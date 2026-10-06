"""Whether an item already has its own designation: a tag, or an assigned one (model-0107).

One index of `facet.assigned_designation` subjects, built once per model digest
(`digest_cached`, the last `DIGEST_CACHE_SIZE`, like `rating_readers`'s and `current_chains`'s):
the first call costs O(F) for F assigned-designation facets, every later call O(1). Lives in
`vocab`, not `derive` (`membership.py`'s own reasoning, design/foundations.md 4): `vocab.validators`
and `derive.designation.own_designation_or_none` both need this one raw fact, so it lives where
both sides can reach it, and neither keeps its own copy (CLAUDE.md red flag).
"""

from typing import TYPE_CHECKING

from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, digest_cached

from .facets.assigned_designation import AssignedDesignationFacet
from .tables import facets_of

if TYPE_CHECKING:
    from fransys_model.kernel import Model

    from .core import Item


@digest_cached(DIGEST_CACHE_SIZE)
def _assigned_subjects(model: Model) -> frozenset[Id[Item]]:
    return frozenset(facet.subject for facet in facets_of(model, AssignedDesignationFacet).values())


def has_own_designation(model: Model, item: Item) -> bool:
    """Whether `item` has a tag or an assigned designation: the raw fact, never the text.

    `own_designation_or_none` (the text) and the `HARNESS_WITHOUT_TAG` gate both call this;
    neither keeps its own tag-or-facet check.
    """
    return item.tag is not None or item.id in _assigned_subjects(model)
