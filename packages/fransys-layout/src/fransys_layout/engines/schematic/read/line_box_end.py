"""Layout-0206: a plug-less line end whose connector stands as a box, its pin views not drawn.

A nested unit's interface or a boxed connector whose pin views left their columns has no pin on
the page, but its box stands there: the line ends at the box, on the edge facing its route.
"""

from typing import TYPE_CHECKING, Any

from fransys_layout.stages.line_draw import EndOnPage

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.stages.connector_boxes import PlacedConnectorBox
    from fransys_model.derive import HarnessLineEnd
    from fransys_model.kernel import Id

type _Page = tuple[int, int]


def boxed_end(
    end: HarnessLineEnd,
    page: _Page,
    boxes: Mapping[Id[Any], Mapping[_Page, PlacedConnectorBox]],
    owner_of: Mapping[Id[Any], Id[Any]],
    toward: tuple[int, int] | None = None,
) -> EndOnPage | None:
    """The end as its connector's box on `page`, or `None` when no such box stands there."""
    for function in dict.fromkeys(owner_of[port] for port in end.ports):
        box = boxes.get(function, {}).get(page)
        if box is not None:
            return EndOnPage(end.branch, interface=True, box=box.box, toward=toward)
    return None


def rows_of(ends: Sequence[EndOnPage]) -> tuple[int, int] | None:
    """The page rows (top, bottom) the given ends stand in: their boxes, else their pins."""
    rows = [y for one in ends for y in _ys(one)]
    return (min(rows), max(rows)) if rows else None


def _ys(one: EndOnPage) -> list[int]:
    if one.box is not None:
        return [one.box.y, one.box.y + one.box.height]
    return [pin.end.at.y for pin in one.pins]
