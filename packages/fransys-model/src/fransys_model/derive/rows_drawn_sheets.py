"""Row shapes of a document's drawn pages and sheets, read by `fransys_pdf` (OUTPUT-DOORS).

They sit beside `rows.py`, which is at its ceiling (model-0199).
"""

from decimal import Decimal

from fransys_model.kernel import Id, value
from fransys_model.layout import DrawingSet
from fransys_model.vocab import AspectNode

__all__ = ["CableBlockSize", "ReplicaOnlySet", "SheetGroup", "SheetRow"]


@value
class SheetRow:
    """A sheet's paper and content box in mm, and its grid `module_mm`: what a page is set on."""

    width_mm: int
    height_mm: int
    content_x_mm: int
    content_y_mm: int
    content_width_mm: int
    content_height_mm: int
    module_mm: Decimal


@value
class ReplicaOnlySet:
    """A drawing set dropped as holding only black-box replicas: its id and its `location`."""

    id: Id[DrawingSet]
    location: Id[AspectNode] | None


@value
class SheetGroup:
    """One sheet format a document's drawn pages name: its `name` and its pages' `numbers`."""

    name: str
    numbers: tuple[int, ...]


@value
class CableBlockSize:
    """A laid-out cable block's `width` and `height` in G, and the `module_mm` of its sheet."""

    width: int
    height: int
    module_mm: Decimal
