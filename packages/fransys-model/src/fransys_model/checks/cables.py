"""Validator: cable cores conform to their cable product (design/facets.md)."""

from typing import TYPE_CHECKING, Final

from fransys_model.checks._finding import finding, ordered
from fransys_model.derive.facts.cables import core_count_gaps, wired_cores_past_product
from fransys_model.kernel import Finding, Severity
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import items

if TYPE_CHECKING:
    from fransys_model.kernel import Model

CABLE_CORE_COUNT: Final[str] = "CABLE_CORE_COUNT"
CORE_INDEX_PAST_PRODUCT: Final[str] = "CORE_INDEX_PAST_PRODUCT"


def check_cables(model: Model) -> tuple[Finding, ...]:
    """Check each cable `Item`'s core `Conductor`s match its `cable_product` facet.

    `CABLE_CORE_COUNT`: wired plus open cores differ from `len(core_colours)`, `WARNING` if fewer,
    `ERROR` if more. `CORE_INDEX_PAST_PRODUCT`: a core index outside the product. Sorted.
    """
    found = [
        finding(
            CORE_INDEX_PAST_PRODUCT,
            Severity.ERROR,
            (cable, core),
            f"cable {ref(items(model)[cable])} has core {index}, its product has {want} cores: "
            f"use a core from 1 to {want} or a part with more cores",
        )
        for cable, core, index, want in wired_cores_past_product(model)
    ]
    for cable, product, have, want in core_count_gaps(model):
        text = f"cable {ref(items(model)[cable])} carries {have} cores, its product has {want}"
        if have < want:
            text += ": wire it, or mark it with W1.spare(...)"
        severity = Severity.WARNING if have < want else Severity.ERROR
        found.append(finding(CABLE_CORE_COUNT, severity, (cable, product), text))
    return ordered(found)
