"""Fold phase 2: once x is solved, a row's flags stagger together and the footprints hold it (R565).

Phase 1 (`place_env`) folds before x with each symbol's own flags; the markers stage staggers a
whole row's, so the page's symbols are folded again from their bare views, by the one `folded`.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .anchors import folded
from .place_assemble import placed_at

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .place_env import PageEnv


def _rows(env: PageEnv) -> dict[tuple[str, str], tuple[int, str]]:
    """Per (symbol, pin) at a row's edge the (row, group) its flags stagger in (a card's own)."""
    rows: dict[tuple[str, str], tuple[int, str]] = {}
    for pc in env.pcs.values():
        for cells in pc.lanes:
            rows[cells[0].sym, cells[0].top_pin or ""] = (pc.row, "")
            rows[cells[-1].sym, cells[-1].bottom_pin or ""] = (pc.row, "")
    for r, row in enumerate(env.plan.rows):
        for b in (env.blocks[n] for n in row.blocks if env.blocks[n].is_card and env.blocks[n].anchor):
            rows |= {(b.anchor or "", pin): (r, b.anchor or "") for pin, e in b.pin_edges if e in "NS"}
    return rows


def refolded(env: PageEnv, x: Mapping[str, int]) -> PageEnv:
    """The env whose symbols hold the flags staggered across their row at the solved x."""
    syms = folded(env.bare, env.hangings, env.problem.anchors, placed_at(env, x), _rows(env))
    page = replace(env.problem, symbols=tuple(syms[s.id] for s in env.problem.symbols))
    return replace(env, syms=syms, problem=page)
