"""Facets: cable products, cable instances and their cores (facets.md and examples.md)."""

from decimal import Decimal

from fransys_model.kernel import AuthoringKey, Id, Value, record, value
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Item, Port
from fransys_model.vocab.templates import Part


@value
class CorePair:
    """Two cores that are twisted into a pair, and the core that screens them, if any.

    `cores` are the two 1-based core numbers (a `@value` tuple is variadic; the part lint holds
    the length at two); `screen` is the number of an `SH` core, or `None`.
    """

    cores: tuple[int, ...]
    screen: int | None


@record(kind="facet.cable_product", subject="subject", unique=True)
class CableProductFacet:
    """The core colours and gauge a cable `Part` catalog entry provides.

    Example: the invented 4-core cable example part carries
    `core_colours=("BN", "BK", "GY", "BU")`, `gauge_mm2=Decimal("1.5")`, `shielded=False`.
    The checked core count is `len(core_colours)`, a screen included (SC4, decision model-0082); the
    printed count is `derive.conductor_count`, without the screen (pdf-0039); the part file's own
    `core_count` is the author's checksum, compared by the part lint. `core_colours` is
    deliberately ordered: the position is the core index. `pairs` names the twisted pairs and
    their screens (CC8, decision model-0204; empty for a product with none). Guarded by
    `validators.cables` (`CABLE_CORE_COUNT`) and `validators.colours`
    (`WIRE_COLOUR_UNKNOWN`, one per bad entry).
    """

    id: Id[CableProductFacet]
    key: AuthoringKey
    subject: Id[Part]
    core_colours: tuple[str, ...]
    gauge_mm2: Decimal
    shielded: bool
    pairs: tuple[CorePair, ...] = ()
    ext: frozendict[str, Value] = frozendict()


@record(kind="facet.cable", subject="subject", unique=True)
class CableFacet:
    """The as-installed length of a cable `Item` (facets.md and examples.md 11).

    Example: the invented cable `W012` example carries `length_mm=15000` once
    measured, `None` before it is.
    """

    id: Id[CableFacet]
    key: AuthoringKey
    subject: Id[Item]
    length_mm: int | None
    ext: frozendict[str, Value] = frozendict()


@record(kind="facet.core", subject="subject", unique=True)
class CoreFacet:
    """The index of one cable core `Conductor` (connectivity.md and examples.md 11).

    Example: cable `W012`'s first core carries `index=1`, making core-to-pin assignment
    explicit rather than positional. The core's colour is the carrier's product
    `core_colours[index - 1]`, read by `derive.core_colour` (SC4, decision model-0082): the
    facet stores no colour.
    """

    id: Id[CoreFacet]
    key: AuthoringKey
    subject: Id[Conductor]
    index: int
    ext: frozendict[str, Value] = frozendict()


@record(kind="facet.open_core", subject="subject", unique=False)
class OpenCoreFacet:
    """One core of a cable `Item` with fewer than two ends: a spare, or a screen earthed at one end.

    `index` is the 1-based core number, `at` the port its one end lands on, or `None` when it
    lands nowhere. The core has no `Conductor` (CC1, decision model-0204); several per cable.
    """

    id: Id[OpenCoreFacet]
    key: AuthoringKey
    subject: Id[Item]
    index: int
    at: Id[Port] | None
    ext: frozendict[str, Value] = frozendict()
