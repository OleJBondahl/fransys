"""Facets: PCB board marker and footprint on a `Part` (connectivity.md and facets.md)."""

from fransys_model.kernel import AuthoringKey, Id, Value, record
from fransys_model.vocab.templates import Part


@record(kind="facet.pcb", subject="subject", unique=True)
class PcbFacet:
    """Marks a `Part` as a board; a `Net` whose ports all sit under it needs no conductors.

    Example: the harness board example `Part` (design/examples.md 11) carries
    `revision="B"`. Read by `validators.connectivity` (board-realised nets produce no
    `NET_UNREALISED`).
    """

    id: Id[PcbFacet]
    key: AuthoringKey
    subject: Id[Part]
    revision: str
    ext: frozendict[str, Value] = frozendict()


@record(kind="facet.footprint", subject="subject", unique=True)
class FootprintFacet:
    """The KiCad footprint library and name for a component `Part`.

    Example: a resistor `Part` on the harness board carries
    `library="Resistor_SMD", name="R_0603_1608Metric"`. Read by
    `derive.queries.board_netlist`.
    """

    id: Id[FootprintFacet]
    key: AuthoringKey
    subject: Id[Part]
    library: str
    name: str
    ext: frozendict[str, Value] = frozendict()
