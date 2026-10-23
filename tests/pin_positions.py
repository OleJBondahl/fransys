"""Test helper (R283): the pin positions two different placed symbols share on one page."""

from typing import Any
lazy from collections.abc import Iterable


def shared_pin_positions(pages: Iterable[Any]) -> list[tuple[int, int, int, tuple[str, ...]]]:
    """(page index, x, y, the symbols) for each point where two symbols have a pin."""
    found: list[tuple[int, int, int, tuple[str, ...]]] = []
    for index, page in enumerate(pages):
        owners: dict[tuple[int, int], set[str]] = {}
        for placed in page.placed:
            for pin in placed.pin_xy:
                owners.setdefault((pin.x, pin.y), set()).add(placed.sym)
        found += [(index, x, y, tuple(sorted(s))) for (x, y), s in owners.items() if len(s) > 1]
    return sorted(found)
