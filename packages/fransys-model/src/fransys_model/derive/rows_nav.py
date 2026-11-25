"""Row shapes of `derive.page_nav`: an invisible link's box and a sheet's outline entry (NV2, NV3).

They sit beside `rows.py`, which is at its ceiling (model-0199).
"""

from decimal import Decimal

from fransys_model.kernel import value

__all__ = ["OutlineSheet", "PageAnchor", "ReferenceLink"]


@value
class ReferenceLink:
    """A rectangle of a page, in grid units, that jumps to the destination label `target`."""

    x: int
    y: int
    width: int
    height: int
    target: str


@value
class PageAnchor:
    """The destination label `label` at a point of a page, in absolute mm from its top left: a frame cell's top-left corner."""

    label: str
    x: Decimal
    y: Decimal


@value
class OutlineSheet:
    """One sheet's outline entry: its `title` and the `entries` beneath."""

    destination: str
    title: str
    entries: tuple[str, ...]
