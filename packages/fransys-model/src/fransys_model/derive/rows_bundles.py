"""Row shapes of `derive.bundles`: a trunk of nets and one net's place in it (placement fact 10)."""

from fransys_model.kernel import Id, value
from fransys_model.vocab.core import Function, Port

__all__ = ["Bundle", "BundleCross", "BundleNet", "BundlePole"]


@value
class BundleNet:
    """One net of a bundle: the net's key (its first port) and its pole index, from 0."""

    net: Id[Port]
    pole: int


@value
class BundlePole:
    """One pole of a crossed end: its index there, and the bundle's pole index of the net on it."""

    local: int
    lane: int


@value
class BundleCross:
    """A function end whose poles take the bundle's nets in another order.

    `poles` lists the poles that carry a bundled net, in local pole order.
    """

    function: Id[Function]
    end: int
    poles: tuple[BundlePole, ...]


@value
class Bundle:
    """Nets that travel as one trunk, one lane each in pole order.

    `id` is the first-pole net's key. A pole is the index at the source, the least function end
    the nets meet; an end that takes them in another order is in `crosses`.
    """

    id: Id[Port]
    nets: tuple[BundleNet, ...]
    crosses: tuple[BundleCross, ...] = ()
