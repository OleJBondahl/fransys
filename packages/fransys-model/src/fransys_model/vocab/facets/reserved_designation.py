"""Facet: a designation reserved by a release, never to be reused within its version."""

from fransys_model.kernel import AuthoringKey, Id, Value, record
from fransys_model.vocab.core import UnitRelease


@record(kind="facet.reserved_designation", subject="subject", unique=False)
class ReservedDesignationFacet:
    """A designation that must never be reused within this release's version.

    Written only by the facade (`fransys.build(releases=)`), from a released pin file's
    `retired` entries and from a pin whose item is gone or has moved group or class code
    never by the numbering pass, and never authored by hand. `subject` is the unit
    release it applies to : every instance of that release carries it, so two instances
    agree on what is reserved. `scope` and `code` locate the sibling group the same way a
    pin's own fields do (`derive.unit_relative_key`'s relative key of the enclosing board or
    harness, `None` for none; the class code, `None` for a part-less item -- the one
    spelling of absence, one record one spelling); `code` never gates reuse, a reserved text
    is taken by its `text` alone within its group; `text` is the reserved own label.
    """

    id: Id[ReservedDesignationFacet]
    key: AuthoringKey
    subject: Id[UnitRelease]
    scope: AuthoringKey | None
    code: str | None
    text: str
    ext: frozendict[str, Value] = frozendict()
