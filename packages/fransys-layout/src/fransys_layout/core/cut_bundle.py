"""One bundle's end: it stands for every pin of a lone-cut fan's pins on a page (BUNDLE, R1319, R499) and lists the others' pins in `also`."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection

    from .values import PinRef, RefEnd

__all__ = ("bundled",)


def bundled(end: RefEnd, rest: Collection[PinRef]) -> RefEnd:
    """`end` as the one end of a bundle: it lists the pins of the `rest` that it stands for."""
    return replace(end, also=tuple(p for p in rest if p != end.pin))
