"""The model-only findings: paper, text floor, lost wires, board nets (R258, R267, R305).

They stood in layout's read step; the facade's layout step calls this one instead.
"""

from typing import TYPE_CHECKING

from .board_findings import board_nets_findings
from .connection_findings import undrawn_connection_findings
from .sheet_findings import text_floor_findings, unused_sheet_findings

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.kernel import Finding, Model

    from .placement_skips import Skipped

__all__ = ["read_findings"]


def read_findings(model: Model, skipped: Iterable[Skipped]) -> tuple[Finding, ...]:
    """`SHEET_FORMAT_UNUSED`, `TEXT_TOO_SMALL`, `CONNECTION_TO_UNDRAWN`, `BOARD_NETS_NOT_DRAWN`."""
    return (
        *unused_sheet_findings(model),
        *text_floor_findings(model),
        *undrawn_connection_findings(model, skipped),
        *board_nets_findings(model),
    )
