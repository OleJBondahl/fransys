"""The items that carry a `terminal` facet: the one set derive, layout and vocab read.

Lives in `vocab`, not `derive`, because `vocab.numbering_codes` reads it and `vocab` never imports
`derive`; `derive.terminal_items` is this function.
"""

from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached

from .facets.terminal import TerminalFacet
from .tables import facets_of
lazy from .core import Item


@digest_cached(DIGEST_CACHE_SIZE)
def terminal_items(model: Model) -> frozenset[Id[Item]]:
    """Every item that carries a `terminal` facet, built once per model digest."""
    return frozenset(facet.subject for facet in facets_of(model, TerminalFacet).values())
