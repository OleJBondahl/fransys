"""Cable blocks grouped into part runs: one run per part number, the blocks in their given order."""

from collections import defaultdict
from collections.abc import Iterable  # noqa: TC003 -- signature tests resolve hints at runtime

from .rows_cable_run import CableBlockRef, CableRun

__all__ = ["NO_PART", "cable_runs"]

NO_PART = "No part number"


def cable_runs(blocks: Iterable[CableBlockRef]) -> tuple[CableRun, ...]:
    """`blocks` grouped by part number, parts sorted by it, blocks in their given order.

    Blocks with no part number form the last run, headed `NO_PART`.
    """
    groups: defaultdict[str, list[CableBlockRef]] = defaultdict(list)
    for block in blocks:
        groups[block.mpn].append(block)
    ordered = [*sorted(key for key in groups if key), *([""] if "" in groups else [])]
    return tuple(CableRun(heading=key or NO_PART, blocks=tuple(groups[key])) for key in ordered)
