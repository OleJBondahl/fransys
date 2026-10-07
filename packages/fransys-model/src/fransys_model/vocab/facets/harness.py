"""Facet: the mark that an item is a harness, whether or not a cable hangs under it (HA1)."""

from fransys_model.kernel import AuthoringKey, Id, Value, record
from fransys_model.vocab.core import Item


@record(kind="facet.harness", subject="subject", unique=True)
class HarnessFacet:
    """The authored mark that an `Item` is a harness (model-0171).

    Example: a part-less `W1` carries it before any cable is hung under it, so its plugs print
    `-W1-P1`. `membership.is_harness` reads this mark, or a cable child.
    """

    id: Id[HarnessFacet]
    key: AuthoringKey
    subject: Id[Item]
    ext: frozendict[str, Value] = frozendict()
