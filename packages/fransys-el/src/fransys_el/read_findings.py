"""The model-only findings: paper and lost wires (R258, R267).

They stood in layout's read step; the facade's layout step calls this one instead.
"""

from typing import TYPE_CHECKING

from .connection_findings import undrawn_connection_findings

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.kernel import Finding, Model

    from .placement_skips import Skipped

__all__ = ["read_findings"]


def read_findings(model: Model, skipped: Iterable[Skipped]) -> tuple[Finding, ...]:
    """`CONNECTION_TO_UNDRAWN`."""
    return undrawn_connection_findings(model, skipped)
