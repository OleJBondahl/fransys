"""The natural place of each column key part, set on `Column.order` for the sort in `partition`."""

import dataclasses
from typing import TYPE_CHECKING

from fransys_model.derive import natural_key

from .reading import _places

if TYPE_CHECKING:
    from fransys_layout.stages import Column


def in_key_order(*groups: tuple[Column, ...]) -> tuple[tuple[Column, ...], ...]:
    """Each group's columns with the natural place of each key part, which `partition` sorts by."""
    place = _places(natural_key(str(part)) for group in groups for c in group for part in c.key)
    return tuple(
        tuple(
            dataclasses.replace(c, order=tuple(place[natural_key(str(part))] for part in c.key))
            for c in group
        )
        for group in groups
    )
