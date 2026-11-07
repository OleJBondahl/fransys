"""Stage 2 authored hints: order_pairs, a stable local move on the unit's list.

A hint name is a group, a symbol id or a card's
anchor box (`Hints`): never a block id, which is opaque (layout-0269, layout-0279).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from .values import Finding

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .blocks_members import Env
    from .flow_values import Block
    from .values import Hints

Names = Mapping[str, frozenset[str]]
Pair = tuple[str, str]


def block_names(block: Block, env: Env) -> frozenset[str]:
    """What a hint may call a block: its group, its anchor box, or a symbol in its columns."""
    cells = (c.sym for col in block.columns for ln in env.columns[col].lanes for c in ln.cells)
    return frozenset(n for n in (block.group, block.anchor, *cells) if n)


def apply_hints(blocks: Sequence[Block], hints: Hints, env: Env) -> tuple[list[Block], list[Finding]]:
    """order_pairs and its findings."""
    return order_pairs(blocks, hints.order_pairs, {b.id: block_names(b, env) for b in blocks})


def order_pairs(blocks: Sequence[Block], pairs: Sequence[Pair], names: Names) -> tuple[list[Block], list[Finding]]:
    """While a pair (a before b) is violated, move b's blocks right after a's last block.

    The passes are bounded: a cycle across hints cannot settle and ends in ORDER_HINT_UNMET.
    """
    out: list[Block] = list(blocks)
    for _ in range(len(pairs) * len(out) + 1):
        moved = False
        for pair in pairs:
            sides = _bad_sides(out, pair, names)
            if sides:
                out = _move_after(out, *sides)
                moved = True
        if not moved:
            break
    text = "{} before {} cannot hold with the other order hints"
    return out, [Finding("ORDER_HINT_UNMET", text.format(a, b), None, f"{a},{b}") for a, b in pairs if _bad_sides(out, (a, b), names)]


def _bad_sides(blocks: Sequence[Block], pair: Pair, names: Names) -> tuple[list[int], list[int]] | None:
    """The positions of a's and b's blocks when some b block stands before the last a block."""
    a = [i for i, x in enumerate(blocks) if pair[0] in names[x.id]]
    b = [i for i, x in enumerate(blocks) if pair[1] in names[x.id]]
    if not a or not b or set(a) & set(b) or min(b) > max(a):
        return None
    return a, b


def _move_after(blocks: Sequence[Block], a: Sequence[int], b: Sequence[int]) -> list[Block]:
    """The b blocks, in their order, right after the last a block."""
    moving = set(b)
    rest = [x for i, x in enumerate(blocks) if i not in moving]
    at = sum(1 for i in range(max(a) + 1) if i not in moving)
    return [*rest[:at], *(blocks[i] for i in b), *rest[at:]]
