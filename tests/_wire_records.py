"""The wire records of a design, shared by the fransys and fransys_author tests (it imports only the model)."""

from typing import Any

from fransys_model.vocab import Conductor, WireFacet


def wire_records(d: Any) -> list[Any]:
    """Every wire record of the design, in the order it was written."""
    return [r for r in d.draft().records() if isinstance(r, Conductor | WireFacet)]
