"""Facets: ratings, operating envelopes, and a unit boundary's own values.

Ratings sit on a `FunctionTemplate` or a `Part`, an operating envelope on a `FunctionTemplate`, and
boundary values on a unit's `Boundary`. Decisions model-0079 and model-0081. The field lists live
in `vocab.ratings`, once.
"""

from fransys_model.kernel import AuthoringKey, Id, SchemaError, Value, record
from fransys_model.vocab.ratings import Operating, Rating
from fransys_model.vocab.templates import FunctionTemplate, Part
from fransys_model.vocab.units import Boundary


@record(kind="facet.rating", subject="subject", unique=True)
class RatingFacet:
    """What a `FunctionTemplate` is rated for, e.g. a relay contact's 250 V and 0.5 A.

    Example: the `no_1` contact template of the invented relay part carries
    `rating=Rating(voltage_ac_v=Decimal("250"), current_ac_a=Decimal("0.5"))`.
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
    `rating=Rating(voltage_ac_v=Decimal("500"), current_ac_a=Decimal("24"))`.
    """

    id: Id[PartRatingFacet]
    key: AuthoringKey
    subject: Id[Part]
    rating: Rating
    ext: frozendict[str, Value] = frozendict()


@record(kind="facet.operating", subject="subject", unique=True)
class OperatingFacet:
    """The supply a `FunctionTemplate` needs to run: nominal value and the window it works in.

    Example: the coil template of the invented relay part carries
    `operating=Operating(voltage_dc_v=Decimal("24"), min_voltage_v=Decimal("18"),
    max_voltage_v=Decimal("30"))`.
    """

    id: Id[OperatingFacet]
    key: AuthoringKey
    subject: Id[FunctionTemplate]
    operating: Operating
    ext: frozendict[str, Value] = frozendict()


@record(kind="facet.boundary_values", subject="subject", unique=True)
class BoundaryValuesFacet:
    """What a unit states about one of its `Boundary` records: a rating, an operating, or both.

    Example: the invented `io_board` unit's boundary on connector `X1` carries
    `operating=Operating(voltage_dc_v=Decimal("24"), min_voltage_v=Decimal("18"),
    max_voltage_v=Decimal("30"))`. The subject is the `Boundary`, not its function: one function
    may be the boundary of two units and each states its own values. A facet with neither
    `rating` nor `operating` says nothing and is refused.
    """

    id: Id[BoundaryValuesFacet]
    key: AuthoringKey
    subject: Id[Boundary]
    rating: Rating | None = None
    operating: Operating | None = None
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Refuse a facet whose `rating` and `operating` are both `None`.

        A value of the wrong type is left as it is: `freeze()` reports it.
        """
        if self.rating is None and self.operating is None:
            msg = f"boundary values facet {self.key!r} states neither a rating nor an operating"
            holder = self.id if type(self.id) is Id else None
            raise SchemaError(msg, kind="facet.boundary_values", record_id=holder)
