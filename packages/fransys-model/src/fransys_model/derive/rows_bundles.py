"""Row shapes of `derive.bundles`: a trunk of nets and one net's place in it (placement fact 10)."""

from fransys_model.kernel import Id, value
from fransys_model.vocab.core import Port

__all__ = ["Bundle", "BundleNet"]


@value
class BundleNet:
    """One net of a bundle: the net's key (its first port) and its pole index, from 0."""

    net: Id[Port]
    pole: int


@value
class Bundle:
    """Nets that travel as one trunk, one lane each in pole order.

    `id` is the first-pole net's key. A pole is the index at the source, the least function end
    the nets meet.
    """

    id: Id[Port]
    nets: tuple[BundleNet, ...]
