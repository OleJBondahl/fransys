"""Stage 5, y: the alignments of a page as plain values, in the order they are kept.

An Align is a list of lines; each line is (graph node, shift) pairs that share one y, the
line being y(node) + shift. The builders return them in keep-order: mate, row group, band.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .geometry import pin_xy
from .keys import natural_key
from .pack import cell_node

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .place_env import PageEnv
    from .values import Cell, PinRef

Line = tuple[tuple[str, int], ...]
Mate = tuple["PinRef", "PinRef"]
Where = dict[str, tuple[str, "Cell", int]]


_ROW_GROUP = (
    "row group {}: its members cannot share one y with the stacks; "
    "dropped, shorten the stack or move the members to the same end of their columns"
)
_BAND = (
    "band {}: its cells cannot share one y with the stacks or trunks; dropped, "
    "shorten the stack above the lower cell or take the band off one of them"
)
_MATE = (
    "mate {}: its pins cannot share one y with the stacks or trunks; dropped, "
    "move one symbol to the head of its column or unmate the pair"
)


@dataclass(frozen=True, slots=True)
class Align:
    """One item to keep or drop: `kind` and `subject` name it, `lines` are the levels it asks.

    `note` is the finding's words when it is dropped, so a drop reads no kind.
    """

    kind: str
    subject: str
    lines: tuple[Line, ...]
    note: str = ""


def row_group_aligns(env: PageEnv) -> tuple[Align, ...]:
    """Each row group with its cells at one end of their columns level, head and foot apart."""
    found: dict[tuple[str, str], list[tuple[str, int]]] = {}
    for pc in env.pcs.values():
        for li, cells in enumerate(pc.lanes):
            for end, i in (("head", 0), ("foot", len(cells) - 1)):
                group = env.syms[cells[i].sym].row_group
                if group:
                    found.setdefault((group, end), []).append((cell_node(pc.id, li, i), 0))
    out = []
    for g in sorted({g for g, _ in found}, key=natural_key):
        lines = tuple(
            tuple(line) for end in ("head", "foot") if len(line := found.get((g, end), [])) > 1
        )
        if lines:
            out.append(Align("row_group", g, lines, _ROW_GROUP.format(g)))
    return tuple(out)


def _topmost(env: PageEnv) -> dict[tuple[int, int], list[tuple[str, int]]]:
    """Per (rank, row): the topmost cell of that rank in each lane, columns in natural order."""
    found: dict[tuple[int, int], list[tuple[str, int]]] = {}
    for pc in sorted(env.pcs.values(), key=lambda c: natural_key(c.id)):
        for li, cells in enumerate(pc.lanes):
            top: dict[int, int] = {}
            for i, cell in enumerate(cells):
                rank = env.syms[cell.sym].band
                if rank is not None:
                    top.setdefault(rank, i)
            for rank, i in top.items():
                found.setdefault((rank, pc.row), []).append((cell_node(pc.id, li, i), 0))
    return found


def _band(rank: int, row: int, line: Line) -> Align:
    subject = f"rank {rank}, row {row}"
    return Align("band", subject, (line,), _BAND.format(subject))


def band_aligns(env: PageEnv) -> tuple[Align, ...]:
    """One Align per (rank, row) with two or more lanes, by rank; none when band_align is off."""
    if not env.options.band_align:
        return ()
    found = _topmost(env)
    return tuple(
        _band(rank, row, tuple(found[rank, row]))
        for rank, row in sorted(found)
        if len(found[rank, row]) > 1
    )


def _where(env: PageEnv) -> Where:
    """The cell of each symbol on the page (its first, in natural column order) and its row."""
    where: Where = {}
    for pc in sorted(env.pcs.values(), key=lambda c: natural_key(c.id)):
        for li, cells in enumerate(pc.lanes):
            for i, cell in enumerate(cells):
                where.setdefault(cell.sym, (cell_node(pc.id, li, i), cell, pc.row))
    return where


def _mate_key(pair: Mate) -> tuple[tuple[tuple[tuple[int, int | str], ...], ...], ...]:
    return tuple((natural_key(p.sym), natural_key(p.pin)) for p in pair)


def _level(env: PageEnv, where: Where, pair: Mate) -> Align | None:
    """The Align of a mate whose halves are cells of one row, else None."""
    a, b = pair
    if a.sym == b.sym or a.sym not in where or b.sym not in where:
        return None
    if where[a.sym][2] != where[b.sym][2]:
        return None
    ends = ((a, where[a.sym]), (b, where[b.sym]))
    line = tuple((n, pin_xy(env.syms[p.sym], c, p.pin)[1]) for p, (n, c, _) in ends)
    subject = f"{a.sym}.{a.pin}/{b.sym}.{b.pin}"
    return Align("mate", subject, (line,), _MATE.format(subject))


def _mates(env: PageEnv) -> tuple[list[Align], list[Mate]]:
    """The mates that level, and those with both halves here that cannot (box half, two rows)."""
    where = _where(env)
    here = set(where) | {env.blocks[b].anchor for r in env.plan.rows for b in r.blocks}
    levelled: list[Align] = []
    unmet: list[Mate] = []
    for pair in sorted(env.problem.facts.mates, key=_mate_key):
        if pair[0].sym in here and pair[1].sym in here:
            align = _level(env, where, pair)
            if align is None:
                unmet.append(pair)
            else:
                levelled.append(align)
    return levelled, unmet


def mate_aligns(env: PageEnv) -> tuple[Align, ...]:
    """Each mate whose two halves are cells of one row of this page: the pins share one y."""
    return tuple(_mates(env)[0])


def unmet_mates(env: PageEnv) -> tuple[Mate, ...]:
    """Mates with both halves on this page that no alignment can level: a box half or two rows."""
    return tuple(_mates(env)[1])


def page_aligns(env: PageEnv) -> Sequence[Align]:
    """All alignments of the page in keep-order: mates, then row groups, then band ranks."""
    return (*mate_aligns(env), *row_group_aligns(env), *band_aligns(env))
