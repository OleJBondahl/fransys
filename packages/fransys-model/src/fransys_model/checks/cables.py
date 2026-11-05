"""Validator: cable cores conform to their cable product (design/facets.md)."""

from typing import TYPE_CHECKING, Final

from fransys_model.checks._finding import ordered
from fransys_model.derive.facts.cables import core_count_gaps, wired_cores_past_product
from fransys_model.vocab.codes import finding
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import items
lazy from fransys_model.kernel import Finding

if TYPE_CHECKING:
    from fransys_model.kernel import Model

CABLE_CORES_FEWER: Final[str] = "CABLE_CORES_FEWER"
CABLE_CORES_MORE: Final[str] = "CABLE_CORES_MORE"
CORE_INDEX_PAST_PRODUCT: Final[str] = "CORE_INDEX_PAST_PRODUCT"


def check_cables(model: Model) -> tuple[Finding, ...]:
    """Check each cable `Item`'s core `Conductor`s match its `cable_product` facet.

    `CABLE_CORES_FEWER` or `CABLE_CORES_MORE`: wired plus open cores differ from
    `len(core_colours)`. `CORE_INDEX_PAST_PRODUCT`: a core index outside the product. Sorted.
    """
    found = [
        finding(
            CORE_INDEX_PAST_PRODUCT,
            (cable, core),
            f"cable {ref(items(model)[cable])} has core {index}, its product has {want} cores: use a core from 1 to {want} or a part with more cores",
        )
        for cable, core, index, want in wired_cores_past_product(model)
    ]
    for cable, product, have, want in core_count_gaps(model):
        text = f"cable {ref(items(model)[cable])} carries {have} cores, its product has {want}"
        if have < want:
            text += ": wire it, or mark it with W1.spare(...)"
        code = CABLE_CORES_FEWER if have < want else CABLE_CORES_MORE
        found.append(finding(code, (cable, product), text))
    return ordered(found)
