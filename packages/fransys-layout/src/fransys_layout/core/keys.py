"""The one tie key: natural designation order, H2 before H10 (answers Q16)."""

from __future__ import annotations

import re

_CHUNK = re.compile(r"(\d+)")


def natural_key(text: str) -> tuple[tuple[int, int | str], ...]:
    """Digits compare as numbers, the rest as text; a stable total order on ids."""
    parts = [str(p) for p in _CHUNK.split(text)]
    return tuple((0, int(p)) if p.isdigit() else (1, p) for p in parts if p != "")
