"""layout-0123: which functions of a device form its one box, and which stand apart."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from fransys_layout.stages import FunctionSpec


def split_box(
    group: Sequence[FunctionSpec], box_drawn: Callable[[FunctionSpec], bool]
) -> tuple[list[FunctionSpec], list[FunctionSpec]]:
    """A device's box-drawn functions (two or more) and the rest, which draw on their own."""
    boxed = [spec for spec in group if box_drawn(spec)]
    if len(boxed) < 2:  # noqa: PLR2004 -- the count is the rule's own size (a pair), not a tunable
        return list(group), []
    return boxed, [spec for spec in group if spec not in boxed]
