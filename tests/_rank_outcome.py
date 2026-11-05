"""What RANK-INVARIANCE compares in a solved layout, as plain multisets (no listing order)."""

from collections import Counter
from typing import Any


def outcome(layout: Any) -> dict[str, Any]:
    """Pages, positions, wires, markers, tables and finding codes of a core layout."""
    placed = Counter(repr(p) for page in layout.placement.pages for p in page.placed)
    return {
        "pages": len(layout.placement.pages),
        "placed": placed,
        "wires": Counter(repr(w) for page in layout.routes.pages for w in page.wires),
        "failed": Counter(repr(f) for f in layout.routes.failed),
        "markers": Counter(repr(m) for m in layout.annotations.markers),
        "references": Counter(repr(r) for r in layout.references),
        "findings": Counter(f.code for f in layout.findings),
    }
