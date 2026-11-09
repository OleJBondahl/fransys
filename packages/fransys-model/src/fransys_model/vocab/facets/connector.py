"""Facet: connector shape on a `FunctionTemplate` (design/facets.md)."""

from fransys_model.elecdef import Connector
from fransys_model.kernel import AuthoringKey, Id, Value, record
from fransys_model.vocab.templates import FunctionTemplate


@record(kind="facet.connector", subject="subject", unique=True)
class ConnectorFacet:
    """Style and the elecdef `Connector` (poles, gender) of a connector `FunctionTemplate`.

    Example: a harness housing's connector template carries
    `style="JST-XH", connector=Connector(poles=4, gender=Gender.FEMALE)`, mated via a `Mate` to a
    board-edge connector of the opposite gender (design/examples.md 11, decision model-0446).

    `connector.gender` absent (`None`) means the part file does not state it, which is not `Gender.GENDERLESS`
    (decision model-0080); only `CONNECTOR_WIRED_WITHOUT_MATE` reads it, and only a `MALE` or
    `FEMALE` gender (decision model-0116). `connector.family` stays `None`: the free `style` has no family.

    `marking` is the label printed on the part ("X1"), read like `Port.marking`: `None` means
    the function's name, `""` no label (a shell or earth stud). Derive reads that rule
    (decision model-0071). `mates` names the MPNs it mates with, data only (decision parts-0016).
    """

    id: Id[ConnectorFacet]
    key: AuthoringKey
    subject: Id[FunctionTemplate]
    style: str
    connector: Connector
    marking: str | None = None
    mates: tuple[str, ...] = ()
    ext: frozendict[str, Value] = frozendict()
