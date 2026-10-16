"""Stage 1 check: every drawn symbol stands in exactly one cell per element (layout-0282)."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from .keys import natural_key
from .values import Finding

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .topology_elements import Elem
    from .values import Column, Sym


def cell_findings(
    drawn: Mapping[str, Sym], elems: Mapping[str, Elem], columns: Sequence[Column]
) -> tuple[Finding, ...]:
    """A NO_CELL finding per drawn symbol whose cell count differs from its element count.

    A box has no element and stands in no cell: it is a plain symbol or a card anchor.
    """
    stands = Counter(c.sym for col in columns for lane in col.lanes for c in lane.cells)
    wanted = Counter(e.sym for e in elems.values())
    return tuple(
        Finding("NO_CELL", _text(sym, stands[sym], wanted[sym]), None, sym)
        for sym in sorted(drawn, key=natural_key)
        if wanted[sym] and stands[sym] != wanted[sym]
    )


def _text(sym: str, cells: int, wanted: int) -> str:
    return f"{sym} stands in {cells} cells; its {wanted} elements need one cell each"
