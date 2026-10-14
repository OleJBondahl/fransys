"""`PAGE_UNDERFILLED`: a schematic page whose drawn content covers little of the content box.

A report, never an objective (layout-0179): pages still stack from the top and a column is one
tier. The share is the bounding box of every placed keep-out, route vertex, label box and marker
box over the content box; the reference band and the frame do not count.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from fransys_layout.stages.content import content_box
from fransys_layout.stages.lookups import placed_keepout
from fransys_layout.stages.slices import by_key, page_of
from fransys_model.kernel import Finding, Severity

from .codes import PAGE_UNDERFILLED
from .printed import on_printed

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.geometry import Box
    from fransys_layout.stages import Handle, Layout, SheetFormat

__all__ = ("UNDERFILL_SHARE", "fill_shares", "lint_fill")

# The share of the content box a page's drawn content must cover to be left alone.
UNDERFILL_SHARE = Decimal("0.5")


def _area(boxes: tuple[Box, ...], vertices: tuple[tuple[int, int], ...]) -> int:
    """The area of the bounding box of `boxes` and route `vertices`."""
    xs = [x for box in boxes for x in (box.x, box.x + box.width)] + [x for x, _ in vertices]
    ys = [y for box in boxes for y in (box.y, box.y + box.height)] + [y for _, y in vertices]
    return (max(xs) - min(xs)) * (max(ys) - min(ys))


def fill_shares(layout: Layout, *, sheet: SheetFormat) -> dict[tuple[int, int], Decimal]:
    """The share of the content box each placed page's drawn content covers, by `(set, page)`."""
    content = content_box(sheet)
    whole = Decimal(content.width * content.height)
    placed_on = by_key(layout.placed, page_of)
    routes_on = by_key(layout.routes, page_of)
    texts_on = by_key((*layout.labels, *layout.markers), page_of)
    found = {}
    for here, placed in sorted(placed_on.items()):
        boxes = (*map(placed_keepout, placed), *(one.box for one in texts_on.get(here, ())))
        vertices = tuple((p.at.x, p.at.y) for r in routes_on.get(here, ()) for p in r.points)
        found[here] = Decimal(_area(boxes, vertices)) / whole
    return found


def lint_fill(
    layout: Layout,
    *,
    sheet: SheetFormat,
    pin_functions: Mapping[Handle, Handle] | None = None,
    printed: frozenset[int] | None = None,
) -> tuple[Finding, ...]:
    """One `PAGE_UNDERFILLED` (INFO) per schematic page under `UNDERFILL_SHARE`, by page.

    A pin view is placed under its port's handle; `pin_functions` maps it to its real function.
    A page of a set that is not in `printed` gets none (model-0201).
    """
    named = pin_functions or {}
    placed_on = by_key(layout.placed, page_of)
    findings = []
    for here, share in fill_shares(layout, sheet=sheet).items():
        if share >= UNDERFILL_SHARE or not on_printed(here, printed):
            continue
        findings.append(
            Finding(
                code=PAGE_UNDERFILLED,
                severity=Severity.INFO,
                subjects=tuple(
                    sorted({named.get(one.function, one.function) for one in placed_on[here]})
                ),
                message=f"drawn content covers {int(share * 100)} % of the content box",
            )
        )
    return tuple(findings)
