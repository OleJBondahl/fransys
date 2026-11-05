"""Facets: ratings and operating envelopes.

Ratings sit on a `FunctionTemplate` or a `Part`, an operating envelope on a `FunctionTemplate`. Decision model-0079. A rating is an elecdef
`Rating`; a protective device's breaking figures are the elecdef `Block` of a `BlockFacet`.
"""

from fransys_model.elecdef import Block, Rating
from fransys_model.kernel import AuthoringKey, Id, Value, record
from fransys_model.vocab.operating import Operating
from fransys_model.vocab.templates import FunctionTemplate, Part


@record(kind="facet.rating", subject="subject", unique=True)
class RatingFacet:
    """What a `FunctionTemplate` is rated for, e.g. a relay contact's 250 V and 0.5 A.

    Example: the `no_1` contact template of the invented relay part carries
    `rating=Rating(voltage=(Range(Role.RATED, nom=Unit.V(250), at=At(Current.AC)),))`.
    """

    id: Id[RatingFacet]
    key: AuthoringKey
    subject: Id[FunctionTemplate]
    rating: Rating
    ext: frozendict[str, Value] = frozendict()


@record(kind="facet.part_rating", subject="subject", unique=True)
class PartRatingFacet:
    """What a whole `Part` is rated for, when the datasheet gives one rating for the device.

    Example: an invented terminal block part carries
    `rating=Rating(voltage=(Range(Role.RATED, nom=Unit.V(500), at=At(Current.AC)),))`.
    """

    id: Id[PartRatingFacet]
    key: AuthoringKey
    subject: Id[Part]
    rating: Rating
    ext: frozendict[str, Value] = frozendict()


@record(kind="facet.block", subject="subject", unique=True)
class BlockFacet:
    """The elecdef block of a protective `FunctionTemplate` that states breaking figures (R783 Q1).

    A fuse link part states its block in a part-level `[block]`, which is the block of its one template (R853).

    Example: the template of a partial-range battery fuse carries
    `block=Fuse(breaking_capacity=(Range(Role.RATED, min=Unit.A(4000)),))`; an mcb carries a `Breaker`
    with `icu` set. Fuse figures are `breaking_capacity`, a breaker's are `icn`, `icu` and `ics`.
    """

    id: Id[BlockFacet]
    key: AuthoringKey
    subject: Id[FunctionTemplate]
    block: Block
    ext: frozendict[str, Value] = frozendict()


@record(kind="facet.operating", subject="subject", unique=True)
class OperatingFacet:
    """The supply a `FunctionTemplate` needs to run: nominal value and the window it works in.

    Example: the coil template of the invented relay part carries
    `operating=Operating(voltage=(Range(Role.RATED, nom=Unit.V(24), min=Unit.V(18), max=Unit.V(30)),))`.
    """

    id: Id[OperatingFacet]
    key: AuthoringKey
    subject: Id[FunctionTemplate]
    operating: Operating
    ext: frozendict[str, Value] = frozendict()
