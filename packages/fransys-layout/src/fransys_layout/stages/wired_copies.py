"""Copies of a function that no wire meets are left out (layout-0214).

The caller names the functions under the rule, each wire end and the ones kept whatever their
wires; `without_unwired_copies` says which copy draws a wire.
"""

from collections import Counter
from dataclasses import replace
from typing import TYPE_CHECKING

from fransys_layout.stages.types import Home

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from fransys_layout.stages.types import Cell, Column, Handle, OrderHint, PageHints

type Copy = tuple[int, int]  # (column index, cell index)


def without_unwired_copies(
    columns: tuple[Column, ...],
    under: AbstractSet[Handle],
    pairs: Iterable[tuple[Handle, Handle]],
    kept: AbstractSet[Handle],
    seats: AbstractSet[tuple[Handle, int]] = frozenset(),
) -> tuple[Column, ...]:
    """`columns` without the copies of `under` that draw none of `pairs` (function, far end).

    A copy in `seats` (function, column index) draws an end of its own. A column left with no
    cell goes too.
    """
    copies = _copies(columns, under)
    drawn = {c for function, i in seats for c in copies.get(function, ()) if c[0] == i}
    whole = set(kept)
    stands = _stands(columns)
    for function, far in pairs:
        if function not in copies or function in whole:
            continue
        picks = [_pick(columns, copies[function], at) for at in stands.get(far, ())]
        if not picks or None in picks:
            whole.add(function)
        drawn.update(pick for pick in picks if pick is not None)
    drawn |= _fanned_homes(columns, copies, drawn)
    gone = {
        copy for function, found in copies.items() if function not in whole for copy in found
    } - drawn
    return _dropped(columns, gone)


def _fanned_homes(
    columns: tuple[Column, ...], copies: Mapping[Handle, list[Copy]], drawn: AbstractSet[Copy]
) -> set[Copy]:
    """The homes of a set where two or more copies draw: the one-copy-per-page drop joins them."""
    found: set[Copy] = set()
    for found_copies in copies.values():
        drawing = Counter(columns[c[0]].drawing_set_key for c in found_copies if c in drawn)
        found.update(
            c
            for c in found_copies
            if drawing[columns[c[0]].drawing_set_key] > 1
            and _cell(columns, c).home is not Home.ELSEWHERE
        )
    return found


def _copies(columns: tuple[Column, ...], under: AbstractSet[Handle]) -> dict[Handle, list[Copy]]:
    found: dict[Handle, list[Copy]] = {}
    for i, column in enumerate(columns):
        for j, cell in enumerate(column.cells):
            if cell.function in under:
                found.setdefault(cell.function, []).append((i, j))
    return found


def _stands(columns: tuple[Column, ...]) -> dict[Handle, list[int]]:
    """Each function's columns, by index."""
    found: dict[Handle, list[int]] = {}
    for i, column in enumerate(columns):
        for cell in column.cells:
            found.setdefault(cell.function, []).append(i)
    return found


def _pick(columns: tuple[Column, ...], copies: Sequence[Copy], far: int) -> Copy | None:
    """The copy that draws a wire to the far end in column `far`; `None` when its set has none."""
    there = columns[far]
    same = [c for c in copies if columns[c[0]].drawing_set_key == there.drawing_set_key]
    if not same:
        return None
    grouped = [c for c in same if columns[c[0]].group == there.group]
    homes = [c for c in same if _cell(columns, c).home is not Home.ELSEWHERE]
    return (grouped or homes or same)[0]


def _cell(columns: tuple[Column, ...], copy: Copy) -> Cell:
    return columns[copy[0]].cells[copy[1]]


def _dropped(columns: tuple[Column, ...], gone: AbstractSet[Copy]) -> tuple[Column, ...]:
    kept = (
        replace(column, cells=tuple(c for j, c in enumerate(column.cells) if (i, j) not in gone))
        for i, column in enumerate(columns)
    )
    return tuple(column for column in kept if column.cells)


def emptied_groups(before: tuple[Column, ...], after: tuple[Column, ...]) -> frozenset[Handle]:
    """The groups that had a column in `before` and have none in `after`."""
    left = {c.group for c in after}
    return frozenset(c.group for c in before if c.group is not None and c.group not in left)


def without_groups(hints: PageHints, groups: AbstractSet[Handle]) -> PageHints:
    """`hints` with `groups` taken out; an order pair through one is bridged."""
    if not groups:
        return hints
    return replace(
        hints,
        break_before=tuple(g for g in hints.break_before if g not in groups),
        keep_together=tuple(
            replace(t, groups=tuple(g for g in t.groups if g not in groups))
            for t in hints.keep_together
            if any(g not in groups for g in t.groups)
        ),
        order=_bridged(hints.order, groups),
    )


def _bridged(order: tuple[OrderHint, ...], groups: AbstractSet[Handle]) -> tuple[OrderHint, ...]:
    """Each pair between kept groups, joining through the taken-out ones."""
    after: Mapping[Handle, list[Handle]] = _successors(order)
    result = []
    for hint in order:
        if hint.before in groups:
            continue
        result.extend(replace(hint, after=target) for target in _reach(hint.after, after, groups))
    return tuple(dict.fromkeys(result))


def _successors(order: tuple[OrderHint, ...]) -> dict[Handle, list[Handle]]:
    found: dict[Handle, list[Handle]] = {}
    for hint in order:
        found.setdefault(hint.before, []).append(hint.after)
    return found


def _reach(
    start: Handle, after: Mapping[Handle, list[Handle]], groups: AbstractSet[Handle]
) -> list[Handle]:
    """The first kept groups at or after `start` along `after`."""
    found, todo, seen = [], [start], set()
    while todo:
        group = todo.pop(0)
        if group in seen:
            continue
        seen.add(group)
        if group in groups:
            todo.extend(after.get(group, ()))
        else:
            found.append(group)
    return found
