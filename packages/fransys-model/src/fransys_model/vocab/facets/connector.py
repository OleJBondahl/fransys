"""Facet: connector shape on a `FunctionTemplate` (design/facets.md)."""

from fransys_model.kernel import AuthoringKey, Id, Value, record
from fransys_model.vocab.enums import Gender
from fransys_model.vocab.templates import FunctionTemplate


@record(kind="facet.connector", subject="subject", unique=True)
class ConnectorFacet:
    """Style, pin count and gender of a connector `FunctionTemplate`.

    Example: a harness housing's connector template carries
    `style="JST-XH", pincount=4, gender=Gender.FEMALE`, mated via a `Mate` to a
    board-edge connector of the opposite gender (design/examples.md 11).

    `gender` absent (`None`) means the part file does not state it, which is not `Gender.NEUTRAL`
    (decision model-0080); only `CONNECTOR_WIRED_WITHOUT_MATE` reads it, and only a `MALE` or
    `FEMALE` gender (decision model-0116).

    `marking` is the label printed on the part ("X1"), read like `Port.marking`: `None` means
    the function's own name is the label, `""` means the connector prints no label (a shell or
    an earth stud, whose pins print under the item). Derive reads that rule, not this record
    (decision model-0071).
    """

    id: Id[ConnectorFacet]
    key: AuthoringKey
    subject: Id[FunctionTemplate]
    style: str
    pincount: int
    gender: Gender | None = None
    marking: str | None = None
    ext: frozendict[str, Value] = frozendict()
