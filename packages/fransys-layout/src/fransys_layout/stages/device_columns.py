"""LC2 (layout-0215): each device chain stands as one column, a device a row, top to bottom."""

from typing import TYPE_CHECKING

from .columns import build_column
from .types import Cell

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .types import Column, DeviceChain, FunctionSpec


def device_columns(
    chains: Sequence[DeviceChain], functions: Sequence[FunctionSpec]
) -> tuple[Column, ...]:
    """One column per chain, keyed by its first device, each member one row in chain order."""
    spec_of = {spec.function: spec for spec in functions}
    return tuple(
        build_column(
            spec_of[chain.members[0]].key,
            tuple(Cell(function=member, index=row) for row, member in enumerate(chain.members)),
            [spec_of[member] for member in chain.members],
        )
        for chain in chains
    )
