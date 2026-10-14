"""Stage 4, place: settle the bands, raising rows to a shared top (place.py)."""

from functools import partial
from typing import TYPE_CHECKING

from fransys_layout.geometry import flow

from ._band_align import _band_top, _cascade_bottom, _participants
from ._row_align import _apply, _row_bottom

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from .place import _Cell, _GapsOf

_Member = tuple[int, int]


def _align_bands(
    page: Sequence[list[list[_Cell]]],
    ranks: frozendict[str, int],
    gaps_of: _GapsOf,
    *,
    floor: int,
    stacked: Mapping[tuple[int, int], int],
) -> None:
    """Align each band's participants, top band first, after spacing (layout-0061)."""
    found = _participants(page)
    aligned: dict[int, set[int]] = {}
    blocks = partial(_blocks, page, gaps_of, aligned)
    fits = partial(_fits, page, gaps_of, floor)
    for band in sorted(found, key=lambda key: (ranks[key[0]], key[0], str(key[1]))):
        if band[0].endswith(".last"):
            continue
        top, members = _settle_band(page, found[band], stacked, blocks, fits)
        if len(members) < 2:  # noqa: PLR2004 -- the count is the rule's own size (a pair or triple), not a tunable
            continue
        for column, index in members:
            _bring_to(page[column], index, top, gaps_of(page[column]))
            aligned.setdefault(column, set()).add(index)


def _blocks(
    page: Sequence[list[list[_Cell]]],
    gaps_of: _GapsOf,
    aligned: Mapping[int, set[int]],
    member: _Member,
    top: int,
) -> bool:
    """Whether bringing `member` to `top` would move a row some band already aligned."""
    rows = page[member[0]]
    return _moves_an_aligned_row(rows, member[1], top, gaps_of(rows), aligned.get(member[0], set()))


def _fits(
    page: Sequence[list[list[_Cell]]], gaps_of: _GapsOf, floor: int, member: _Member, top: int
) -> bool:
    """Whether lowering `member` to `top` keeps its column above `floor`."""
    rows = page[member[0]]
    return _cascade_bottom(rows, member[1], top, gaps_of(rows)) <= floor


def _settle_band(
    page: Sequence[list[list[_Cell]]],
    members: Sequence[_Member],
    stacked: Mapping[_Member, int],
    blocks: Callable[[_Member, int], bool],
    fits: Callable[[_Member, int], bool],
) -> tuple[int, list[_Member]]:
    """Drop participants until the rest share one top; return that top and who stays."""
    top = 0
    members = list(members)
    while len(members) > 1:
        top = _band_top(page, members, stacked)
        blockers = [m for m in members if blocks(m, top)]
        if not blockers and all(fits(m, top) for m in members):
            break
        # the participant that can rise least leaves the band
        members.remove(max(blockers or members, key=lambda m: (stacked[m], m)))
    return top, members


def _bring_to(rows: Sequence[list[_Cell]], index: int, top: int, gaps: Sequence[int]) -> None:
    """Move `rows[index]` to `top`: raise it from below, cascade it from above."""
    current = min(cell.top for cell in rows[index])
    if current > top:
        _raise(rows, index, top, gaps)
    elif current < top:
        _cascade(rows, index, top, gaps)


def _moves_an_aligned_row(
    rows: Sequence[list[_Cell]],
    index: int,
    top: int,
    gaps: Sequence[int],
    aligned: AbstractSet[int],
) -> bool:
    """Whether bringing `rows[index]` to `top` would move a row of `aligned` (layout-0061)."""
    current = min(cell.top for cell in rows[index])
    if current > top:
        moves = _raise_plan(rows, index, top, gaps)
    elif current < top:
        moves = _cascade_plan(rows, index, top, gaps)
    else:
        return False
    return any(row in aligned for row, _ in moves)


def _raise(rows: Sequence[list[_Cell]], start: int, top: int, gaps: Sequence[int]) -> None:
    """Raise `rows[start]` to `top`; the rows above it move up only as far as they must."""
    for index, shift in _raise_plan(rows, start, top, gaps):
        for cell in rows[index]:
            cell.at_top(cell.top - shift)


def _raise_plan(
    rows: Sequence[list[_Cell]], start: int, top: int, gaps: Sequence[int]
) -> list[tuple[int, int]]:
    """The moves of `_raise` as (row index, shift up), the start row first."""
    shift = min(cell.top for cell in rows[start]) - top
    moves = [(start, shift)]
    below = min(cell.top_at(cell.top - shift) for cell in rows[start])
    for index in range(start - 1, -1, -1):
        excess = max(cell.bottom for cell in rows[index]) - (below - gaps[index])
        if excess <= 0:
            break
        moves.append((index, excess))
        below = min(cell.top_at(cell.top - excess) for cell in rows[index])
    return moves


def _cascade(rows: Sequence[list[_Cell]], start: int, top: int, gaps: Sequence[int]) -> None:
    """Lower `rows[start]` to `top` and push the rows below just far enough to follow."""
    _apply(rows, _cascade_plan(rows, start, top, gaps))


def _cascade_plan(
    rows: Sequence[list[_Cell]], start: int, top: int, gaps: Sequence[int]
) -> list[tuple[int, int]]:
    """The moves of `_cascade` as (row index, new top), the start row first."""
    moves = flow(
        rows[start:],
        floor=top,
        gaps=gaps[start:],
        far_edge=_row_bottom,
        near_edge=lambda row: min(cell.top for cell in row),
    )
    return [(start + index, new_top) for index, new_top in moves]
