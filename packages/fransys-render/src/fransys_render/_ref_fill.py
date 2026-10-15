"""A net reference's fill: the tint of its net's colour slot as an inline style (render-0013)."""

from typing import TYPE_CHECKING

from fransys_model.derive.drawing_text import REF_SLOTS, reference_slot

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_model.kernel import Model
    from fransys_model.layout import LinkMarker


def checked_tints(tints: Sequence[str]) -> Sequence[str]:
    """`tints` itself when empty (no fills) or exactly `REF_SLOTS` long; else `ValueError`."""
    if tints and len(tints) != REF_SLOTS:
        msg = f"expected {REF_SLOTS} tints or none, got {len(tints)}"
        raise ValueError(msg)
    return tints


def ref_fill(model: Model, marker: LinkMarker, tints: Sequence[str]) -> str:
    """` style="fill:#rrggbb"` for a numbered reference, else empty.

    Inline style, because the page rule `.marker { fill: none }` beats a fill attribute.
    """
    slot = reference_slot(model, marker) if tints else None
    return "" if slot is None else f' style="fill:{tints[slot]}"'
