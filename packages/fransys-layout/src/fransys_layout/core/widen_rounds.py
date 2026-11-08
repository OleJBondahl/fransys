"""Stage 7, widen: the bound of its pass loop (R1981)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .errors import CoreError

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .outputs import Demand
    from .values import Options


def settled(rounds: int, options: Options, asked: Iterable[Demand], *, quiet: bool) -> bool:
    """Whether pass `rounds` ended the loop: a quiet pass after the first; a busy one past `widen_rounds_limit` raises.

    Grants only grow, so a pass that still grants after the limit is a loop, never a hang.
    """
    if not quiet and rounds >= options.widen_rounds_limit:
        msg = f"widen granted again after {rounds} rounds; unmet room asks: {[(d.owner, d.side, d.room, d.box) for d in asked]}"
        raise CoreError(msg)
    return bool(rounds) and quiet
