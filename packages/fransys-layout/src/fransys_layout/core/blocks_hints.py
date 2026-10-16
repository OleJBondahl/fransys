"""Stage 2 authored hints: order_pairs, chains, keep_together, break_before, in that order.

Each is a stable local move on the unit's list. A hint name is a group, a symbol id or a card's
anchor box (`Hints`): never a block id, which is opaque (layout-0269, layout-0279).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import TYPE_CHECKING

from .values import Finding

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .blocks_members import Env
    from .values import Block, Hints

Names = Mapping[str, frozenset[str]]
Pair = tuple[str, str]


def block_names(block: Block, env: Env) -> frozenset[str]:
    """What a hint may call a block: its group, its anchor box, or a symbol in its columns."""
    cells = (c.sym for col in block.columns for ln in env.columns[col].lanes for c in ln.cells)
    return frozenset(n for n in (block.group, block.anchor, *cells) if n)


def apply_hints(
    blocks: Sequence[Block], hints: Hints, env: Env
) -> tuple[list[Block], list[Finding]]:
    """order_pairs, chains, keep_together, break_before; the findings of the first and third."""
    names = {b.id: block_names(b, env) for b in blocks}
    out, unordered = order_pairs(blocks, hints.order_pairs, names)
    out = [chain(b, hints.chains, env) for b in out]
    page = env.problem.area.w - 2 * env.options.margin.w
    out, split = keep_together(out, hints.keep_together, names, page, env.options.column_gap_min)
    return break_before(out, hints.break_before), [*unordered, *split]


def order_pairs(
    blocks: Sequence[Block], pairs: Sequence[Pair], names: Names
) -> tuple[list[Block], list[Finding]]:
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
    return out, [
        Finding("ORDER_HINT_UNMET", text.format(a, b), None, f"{a},{b}")
        for a, b in pairs
        if _bad_sides(out, (a, b), names)
    ]


def _bad_sides(
    blocks: Sequence[Block], pair: Pair, names: Names
) -> tuple[list[int], list[int]] | None:
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


def chain(block: Block, chains: Sequence[Sequence[str]], env: Env) -> Block:
    """The columns of a chain in a block take the chain's order in the slots they fill; fixed then.

    A card keeps its pin order, so a chain leaves it alone.
    """
    if block.kind == "card":
        return block
    col_of = {
        c.sym: col for col in block.columns for ln in env.columns[col].lanes for c in ln.cells
    }
    cols = list(block.columns)
    fixed = False
    for names in chains:
        want = list(dict.fromkeys(col_of[s] for s in names if s in col_of))
        if len(want) > 1:
            for slot, c in zip(sorted(cols.index(w) for w in want), want, strict=True):
                cols[slot] = c
            fixed = True
    return replace(block, columns=tuple(cols), fixed_order=True) if fixed else block


def keep_together(
    blocks: Sequence[Block], sets: Sequence[frozenset[str]], names: Names, page: int, gap: int
) -> tuple[list[Block], list[Finding]]:
    """A set whose blocks fit one page width becomes consecutive at its first block; else a finding.

    The width is the cut's row measure: each block's width_est plus one column gap.
    """
    out: list[Block] = list(blocks)
    unmet: list[Finding] = []
    for members in sets:
        at = [i for i, b in enumerate(out) if members & names[b.id]]
        if len(at) <= 1:
            continue
        subject = ",".join(sorted(members))
        if sum(out[i].width_est + gap for i in at) > page:
            unmet.append(
                Finding(
                    "KEEP_TOGETHER_UNMET", f"{subject} do not fit one page width", None, subject
                )
            )
            continue
        pulled = set(at)
        rest = [b for i, b in enumerate(out) if i not in pulled]
        out = [*rest[: at[0]], *(out[i] for i in at), *rest[at[0] :]]
    return out, unmet


def break_before(blocks: Sequence[Block], groups: frozenset[str]) -> list[Block]:
    """forced_break_before on the first block, in the final order, of each group named."""
    first: dict[str, int] = {}
    for i, b in enumerate(blocks):
        if b.group in groups:
            first.setdefault(b.group, i)
    flagged = set(first.values())
    return [
        replace(b, forced_break_before=True) if i in flagged else b for i, b in enumerate(blocks)
    ]
