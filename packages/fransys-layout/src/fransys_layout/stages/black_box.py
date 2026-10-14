"""Where a nested unit's function stands as a black box: its stubs and rail leads end there.

One rule for `references.black_box_sets` (on seats) and layout-0214's stub seats (on columns).
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Set as AbstractSet

    from fransys_layout.stages.references.types import BlackBoxReads
    from fransys_layout.stages.types import FunctionSpec, Handle


def black_box_tops(
    functions: Iterable[FunctionSpec], reads: BlackBoxReads
) -> dict[Handle, Handle | None]:
    """Each nested unit's edge function, and the top-level unit it stands under."""
    return {
        spec.function: reads.top(spec.unit)
        for spec in functions
        if spec.unit in reads.nested
        and (spec.pin_function in reads.edges or spec.function in reads.edges)
    }


def is_black_box(
    unit: Handle | None,
    set_unit: Handle | None,
    own_top: Handle | None,
    nested: AbstractSet[Handle | None],
) -> bool:
    """Whether a function of `unit` drawn in a set of `set_unit` is a black box there."""
    return unit in nested and unit != set_unit and own_top in (None, set_unit)
