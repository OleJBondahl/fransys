"""Validator: wire colours and cable-product core colours are IEC 60757 codes (model-0070)."""

from typing import TYPE_CHECKING, Final

from fransys_model.kernel import Finding, Severity, key_text
from fransys_model.vocab.colours import COLOUR_GRAMMAR, split_colour
from fransys_model.vocab.enums import ConductorKind
from fransys_model.vocab.facets.cable import CableProductFacet
from fransys_model.vocab.facets.wire import WireFacet
from fransys_model.vocab.tables import conductors, facets_of, parts

if TYPE_CHECKING:
    from fransys_model.kernel import Model

WIRE_COLOUR_UNKNOWN: Final[str] = "WIRE_COLOUR_UNKNOWN"


def check_colours(model: Model) -> tuple[Finding, ...]:
    """Check every wire colour and cable product core colour against `vocab.colours`.

    `WIRE_COLOUR_UNKNOWN` (`ERROR`), one per bad value of a `wire` facet or `core_colours` entry.
    Empty colour is legal; the message states the grammar; sorted by `(code, subjects, message)`.
    """
    all_conductors = conductors(model)
    all_parts = parts(model)
    found: list[Finding] = []
    for facet in facets_of(model, WireFacet).values():
        if split_colour(facet.colour) is not None:
            continue
        conductor = all_conductors[facet.subject]
        what = "core" if conductor.kind is ConductorKind.CORE else "wire"
        found.append(
            Finding(
                code=WIRE_COLOUR_UNKNOWN,
                severity=Severity.ERROR,
                subjects=(conductor.id, facet.id),
                message=(
                    f"{what} {key_text(conductor)} has colour {facet.colour!r}, "
                    f"which is not {COLOUR_GRAMMAR}"
                ),
            )
        )
    for product in facets_of(model, CableProductFacet).values():
        for index, colour in enumerate(product.core_colours, start=1):
            if split_colour(colour) is not None:
                continue
            found.append(
                Finding(
                    code=WIRE_COLOUR_UNKNOWN,
                    severity=Severity.ERROR,
                    subjects=(product.subject, product.id),
                    message=(
                        f"cable part {key_text(all_parts[product.subject])} core colour "
                        f"{index} is {colour!r}, which is not {COLOUR_GRAMMAR}"
                    ),
                )
            )
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
