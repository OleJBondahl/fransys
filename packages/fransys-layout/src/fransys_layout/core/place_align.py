"""Stage 5, y: the alignments of a page as plain values, in the order they are kept.

An Align is a list of lines; each line is (graph node, shift) pairs that share one y, the
line being y(node) + shift. The builders return them in keep-order: mate, row group, band.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .errors import CoreError
from .geometry import pin_xy
from .keys import natural_key
from .outputs import StripRun
from .pack import cell_node

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from .flow_values import Cell
    from .outputs import Placed
    from .place_env import PageEnv
    from .values import PinRef

Line = tuple[tuple[str, int], ...]
Mate = tuple["PinRef", "PinRef"]
Where = dict[str, tuple[str, "Cell", int]]


_ROW_GROUP = (
    "row group {}: its members cannot share one y with the stacks; dropped, shorten the stack or move the members to the same end of their columns"
)
_BAND = (
    "band {}: its cells cannot share one y with the stacks or trunks; dropped, "
    "shorten the stack above the lower cell or take the band off one of them"
)
_MATE = "mate {}: its pins cannot share one y with the stacks or trunks; dropped, move one symbol to the head of its column or unmate the pair"


@dataclass(frozen=True, slots=True)
class Align:
    """One item to keep or drop: `kind` and `subject` name it, `lines` are the levels it asks.

    `note` is the finding's words when it is dropped, so a drop reads no kind.
    """

    kind: str
    subject: str
    lines: tuple[Line, ...]
    note: str = ""


def _ends(env: PageEnv) -> dict[tuple[str, int, str], list[tuple[str, str]]]:
    """Per (row group, page row, head|foot): the (graph node, symbol id) of its cells at that end of their columns."""
    found: dict[tuple[str, int, str], list[tuple[str, str]]] = {}
    for pc in env.pcs.values():
        for li, cells in enumerate(pc.lanes):
            for end, i in (("head", 0), ("foot", len(cells) - 1)):
                if group := env.syms[cells[i].sym].row_group:
                    found.setdefault((group, pc.row, end), []).append((cell_node(pc.id, li, i), cells[i].sym))
    return found


def row_group_aligns(env: PageEnv) -> tuple[Align, ...]:
    """Each row group, per page row, with its cells at one end of their columns level, head and foot apart."""
    found = _ends(env)
    out = []
    for g, row in sorted({(g, r) for g, r, _ in found}, key=lambda k: (natural_key(k[0]), k[1])):
        lines = tuple(tuple((n, 0) for n, _ in line) for end in ("head", "foot") if len(line := found.get((g, row, end), [])) > 1)
        if lines:
            subject = f"{g}, row {row}"
            out.append(Align("row_group", subject, lines, _ROW_GROUP.format(subject)))
    return tuple(out)


def _parts(env: PageEnv, dropped: AbstractSet[str | None]) -> list[tuple[str, list[str]]]:
    """(row group, symbol ids) of each run: a row group's cells level at one end, each alone when its Align was dropped, a mid-column one alone."""
    seen: set[str] = set()
    parts: list[tuple[str, list[str]]] = []
    for (g, row, _), members in _ends(env).items():
        ids = [s for _, s in members if s not in seen]
        seen.update(ids)
        each = [[i] for i in ids] if f"{g}, row {row}" in dropped else [ids]
        parts.extend((g, part) for part in each if part)
    parts.extend(
        (g, [c.sym]) for pc in env.pcs.values() for cells in pc.lanes for c in cells if (g := env.syms[c.sym].row_group) and c.sym not in seen
    )
    return parts


def _beside(ids: Sequence[str], placed: Mapping[str, Placed]) -> list[list[str]]:
    """`ids` (left to right) cut where the gap to the previous one is over one pitch, its footprint width (STRIP-TAG-ONCE)."""
    cuts: list[list[str]] = []
    for i in ids:
        prev = placed[cuts[-1][-1]].footprint if cuts else None
        if prev is not None and placed[i].footprint.x <= prev.x + 2 * prev.w:
            cuts[-1].append(i)
        else:
            cuts.append([i])
    return cuts


def strip_runs(env: PageEnv, dropped: AbstractSet[str | None], placed: Mapping[str, Placed]) -> tuple[StripRun, ...]:
    """The runs of the strip terminals, each in one run, its members left to right and side by side; `dropped` are the Aligns lost."""
    runs = []
    for g, whole in _parts(env, dropped):
        for ids in _beside(whole, placed):
            if (key := f"{g} run at {ids[0]}") in env.syms:
                msg = f"strip {g}: the run key {key!r} is also a symbol id; ids share one space"
                raise CoreError(msg)
            runs.append(StripRun(g, tuple(ids), key))
    return tuple(runs)


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
    """One Align per (rank, row) with two or more lanes, by rank."""
    found = _topmost(env)
    return tuple(_band(rank, row, tuple(found[rank, row])) for rank, row in sorted(found) if len(found[rank, row]) > 1)


def _where(env: PageEnv) -> Where:
    """The cell of each symbol on the page (its first, in natural column order) and its row."""
    where: Where = {}
    for pc in sorted(env.pcs.values(), key=lambda c: natural_key(c.id)):
        for li, cells in enumerate(pc.lanes):
            for i, cell in enumerate(cells):
                where.setdefault(cell.sym, (cell_node(pc.id, li, i), cell, pc.row))
    return where


def _canonical(pair: Mate) -> Mate:
    """The pair with its halves in natural (sym, pin) order, whatever order they arrived in."""
    a, b = sorted(pair, key=lambda p: (natural_key(p.sym), natural_key(p.pin)))
    return a, b


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
    for pair in sorted((_canonical(m) for m in env.problem.facts.mates), key=lambda m: tuple((natural_key(p.sym), natural_key(p.pin)) for p in m)):
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
