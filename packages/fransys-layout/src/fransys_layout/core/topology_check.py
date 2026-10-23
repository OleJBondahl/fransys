"""Stage 1 check: every drawn symbol stands in exactly one cell per element (layout-0282)."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from .errors import CoreError
from .keys import natural_key
from .values import Finding

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .sym_values import Sym
    from .topology_elements import Elem
    from .values import Column


class SymbolInTwoColumnsError(CoreError):
    """One symbol stands in cells of two columns, so it would be placed twice (R283)."""


def cell_findings(
    drawn: Mapping[str, Sym], elems: Mapping[str, Elem], columns: Sequence[Column]
) -> tuple[Finding, ...]:
    """A NO_CELL finding per drawn symbol whose cell count differs from its element count.

    A box has no element and stands in no cell: it is a plain symbol or a card anchor.
    """
    _one_column(columns)
    stands = Counter(c.sym for col in columns for lane in col.lanes for c in lane.cells)
    wanted = Counter(e.sym for e in elems.values())
    return tuple(
        Finding("NO_CELL", _text(sym, stands[sym], wanted[sym]), None, sym)
        for sym in sorted(drawn, key=natural_key)
        if wanted[sym] and stands[sym] != wanted[sym]
    )


def _text(sym: str, cells: int, wanted: int) -> str:
    return f"{sym} stands in {cells} cells; its {wanted} elements need one cell each"


def _one_column(columns: Sequence[Column]) -> None:
    """Raise, naming the symbol and its columns, when a symbol stands in more than one column."""
    homes: dict[str, list[str]] = {}
    for col in columns:
        for lane in col.lanes:
            for c in lane.cells:
                if col.id not in homes.setdefault(c.sym, []):
                    homes[c.sym].append(col.id)
    for sym, cols in homes.items():
        if len(cols) > 1:
            msg = f"{sym} stands in two columns ({', '.join(cols)}): one home only"
            raise SymbolInTwoColumnsError(msg)
