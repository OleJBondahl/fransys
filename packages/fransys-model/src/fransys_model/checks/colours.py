"""Validator: wire colours and cable-product core colours are IEC 60757 codes (model-0070)."""

from typing import TYPE_CHECKING, Final

from fransys_model.checks._finding import finding, ordered
from fransys_model.derive.facts.colours import unknown_core_colours, unknown_wire_colours
from fransys_model.derive.facts.cores import is_core
from fransys_model.kernel import Finding, Severity
from fransys_model.vocab.colours import COLOUR_GRAMMAR
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import conductors, parts

if TYPE_CHECKING:
    from fransys_model.kernel import Model

WIRE_COLOUR_UNKNOWN: Final[str] = "WIRE_COLOUR_UNKNOWN"


def check_colours(model: Model) -> tuple[Finding, ...]:
    """Check every wire colour and cable product core colour against `vocab.colours`.

    `WIRE_COLOUR_UNKNOWN` (`ERROR`), one per bad value of a `wire` facet or `core_colours` entry.
    Empty colour is legal; the message states the grammar; sorted by `(code, subjects, message)`.
    """
    found: list[Finding] = []
    for facet in unknown_wire_colours(model):
        conductor = conductors(model)[facet.subject]
        what = "core" if is_core(model, conductor.id) else "wire"
        text = f"{what} {ref(conductor)} has colour {facet.colour!r}, which is not {COLOUR_GRAMMAR}"
        found.append(finding(WIRE_COLOUR_UNKNOWN, Severity.ERROR, (conductor.id, facet.id), text))
    for product, index, colour in unknown_core_colours(model):
        text = (
            f"cable part {parts(model)[product.subject].mpn} core colour "
            f"{index} is {colour!r}, which is not {COLOUR_GRAMMAR}"
        )
        found.append(
            finding(WIRE_COLOUR_UNKNOWN, Severity.ERROR, (product.subject, product.id), text)
        )
    return ordered(found)
