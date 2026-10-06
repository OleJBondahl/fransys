"""Helpers the derive tests import by name; the name is unique across the workspace."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fransys_model.kernel import Draft, Origin, Record


def add_all(draft: Draft, *records: Record, origin: Origin) -> None:
    """Add every one of `records` to `draft`, all attributed to `origin`."""
    for record in records:
        draft.add(record, origin=origin)
