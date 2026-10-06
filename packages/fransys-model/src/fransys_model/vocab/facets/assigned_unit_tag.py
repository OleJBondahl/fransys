"""Facet: the tag the numbering pass gave a unit instance that has none (UNIT-TAGS UT3)."""

from fransys_model.kernel import AuthoringKey, Id, Value, record
from fransys_model.vocab.core import Unit


@record(kind="facet.assigned_unit_tag", subject="subject", unique=True)
class AssignedUnitTagFacet:
    """The tag the numbering pass gave a unit instance whose `Unit.tag` is `None`.

    Example: a floating instance of a release with `class_code="U"` carries `text="U2"` when
    `U1` is taken. `derive.unit_tag` reads `Unit.tag`, else this text. The facade may write it
    before the pass from a pin file, as it does for `facet.assigned_designation` (FD5), and the
    pass keeps it.
    """

    id: Id[AssignedUnitTagFacet]
    key: AuthoringKey
    subject: Id[Unit]
    text: str
    ext: frozendict[str, Value] = frozendict()
