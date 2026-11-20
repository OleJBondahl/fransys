"""Stage 7, widen: the bound of its pass loop (R1981)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .errors import CoreError

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from .outputs import Demand, Routes
    from .values import Options


def settled(rounds: int, options: Options, asked: Iterable[Demand], *, quiet: bool) -> bool:
    """Whether pass `rounds` ended the loop: a quiet pass after the first; a busy one past `widen_rounds_limit` raises.

    Grants only grow, so a pass that still grants after the limit is a loop, never a hang.
    """
    if not quiet and rounds >= options.widen_rounds_limit:
        msg = f"widen granted again after {rounds} rounds; unmet room asks: {[(d.owner, d.side, d.room, d.box) for d in asked]}"
        raise CoreError(msg)
    return bool(rounds) and quiet


def unspent(tried: Mapping[str, int], routes: Routes, options: Options) -> tuple[dict[str, int], list[Demand]]:
    """The count of rounds each blocked label has stood blocked, and the needs of those still within `label_recut_limit` recuts.

    A label past its limit is asked for no more, so the loop settles and its LABEL_NO_ROOM finding stands (R2486).
    """
    needs = [d for p in routes.pages for d in p.needs]
    tried = {**tried, **{o: tried.get(o, 0) + 1 for o in {d.owner for d in needs if d.owner}}}
    return tried, [d for d in needs if tried.get(d.owner, 0) <= options.label_recut_limit]
