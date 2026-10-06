"""Facets: cable products, cable instances and their cores (facets.md and examples.md)."""

from decimal import Decimal

from fransys_model.kernel import AuthoringKey, Id, Value, record
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Item
from fransys_model.vocab.templates import Part


@record(kind="facet.cable_product", subject="subject", unique=True)
class CableProductFacet:
    """The core colours and gauge a cable `Part` catalog entry provides.

    Example: the invented 4-core cable example part carries
    `core_colours=("BN", "BK", "GY", "BU")`, `gauge_mm2=Decimal("1.5")`, `shielded=False`.
    The core count is `len(core_colours)` (SC4, decision model-0082); the part file's own
    `core_count` is the author's checksum, compared by the part lint. `core_colours` is
    deliberately ordered: the position is the core index. Guarded by `validators.cables`
    (`CABLE_CORE_COUNT`) and `validators.colours` (`WIRE_COLOUR_UNKNOWN`, one per bad entry).
    """

    id: Id[CableProductFacet]
    key: AuthoringKey
    subject: Id[Part]
    core_colours: tuple[str, ...]
    gauge_mm2: Decimal
    shielded: bool
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
