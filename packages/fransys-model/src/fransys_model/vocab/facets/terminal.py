"""Facet: terminal identity within a strip (design/facets.md)."""

from fransys_model.kernel import AuthoringKey, Id, Value, record
from fransys_model.vocab.core import Item


@record(kind="facet.terminal", subject="subject", unique=True)
class TerminalFacet:
    """Which group and position a terminal `Item` occupies on its strip.

    Example: the third terminal of strip `X03`'s `L1` group carries
    `group="L1", index=3`; its designation `L1:3` is derived, never stored (DESIGN
    11). Cardinality (at most one per subject, design/facets.md) is a freeze-time concern,
    not a vocab validator's.
    """

    id: Id[TerminalFacet]
    key: AuthoringKey
    subject: Id[Item]
    group: str
    index: int
    ext: frozendict[str, Value] = frozendict()
