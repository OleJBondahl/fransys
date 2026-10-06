"""Facet: the designation the numbering pass gave an item (facets.md and derive.md)."""

from fransys_model.kernel import AuthoringKey, Id, Value, record
from fransys_model.vocab.core import Item


@record(kind="facet.assigned_designation", subject="subject", unique=True)
class AssignedDesignationFacet:
    """The designation the numbering pass gave an item that has no tag.

    Example: an untagged relay with class code `K` carries `text="K1"`; `derive.item_designation`
    reads the item's tag, else this text. The numbering pass is the writer today. A later writer
    (the facade, from a pin file) may write it before the pass runs, and the pass then keeps it
    and takes its text as used.
    """

    id: Id[AssignedDesignationFacet]
    key: AuthoringKey
    subject: Id[Item]
    text: str
    ext: frozendict[str, Value] = frozendict()
