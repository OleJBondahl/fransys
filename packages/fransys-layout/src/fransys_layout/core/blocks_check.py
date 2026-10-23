"""Stage 2 check: every drawn box is the anchor of exactly one block (layout-0283)."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from .keys import natural_key
from .values import Finding

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from .sym_values import Sym
    from .values import Block


def box_findings(
    drawn: Iterable[str], syms: Mapping[str, Sym], blocks: Sequence[Block]
) -> tuple[Finding, ...]:
    """A NO_BLOCK finding per drawn box that no block, or more than one, is anchored on."""
    held = Counter(b.anchor for b in blocks if b.anchor)
    return tuple(
        Finding("NO_BLOCK", _text(box, held[box]), None, box)
        for box in sorted(drawn, key=natural_key)
        if syms[box].box is not None and held[box] != 1
    )


def _text(box: str, blocks: int) -> str:
    return f"{box} is drawn in {blocks} blocks; every drawn box belongs to exactly one"
