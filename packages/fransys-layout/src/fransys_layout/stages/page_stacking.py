"""The inputs of one page's stacking, the rule `place` and `page_stack` stack by (S12)."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .references.digits import FLOOR

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.geometry import Box

    from .references.digits import Digits
    from .texts.stand import PageTexts
    from .types import Handle, Profile, SheetFormat


@dataclass(frozen=True, slots=True)
class PageStacking:
    """What `place` and `page_stack` both stack a page by, so each port's offset agrees (S12)."""

    profile: Profile
    sheet: SheetFormat
    headroom_lanes: int = 0
    bottom_headroom_lanes: int = 0
    label_boxes: Mapping[Handle, list[tuple[str, Box]]] = field(default_factory=frozendict)
    texts: PageTexts | None = None
    # S4: the page's set's digits, so the band `place` reserves is as wide as the box it holds
    digits: Digits = FLOOR
    # HL18 (layout-0158): each (function, port) a line's conductor lands on
    line_ends: frozenset[tuple[Handle, Handle]] = frozenset()
