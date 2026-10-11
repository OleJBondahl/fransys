"""Where a line end is drawn, as a stub names it: plain values per page."""

from typing import TYPE_CHECKING, Any, Protocol

from fransys_model.vocab.tables import ports

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.stages.connector_boxes import PlacedConnectorBox
    from fransys_layout.stages.types import PlacedFunction
    from fransys_model.derive import HarnessLineEnd
    from fransys_model.kernel import Id, Model

    from .harness_lines import LineReads

type Page = tuple[int, int]
type Spots = dict[Page, tuple[int, int]]


def end_spots(
    model: Model,
    end: HarnessLineEnd,
    boxes: Mapping[Id[Any], Mapping[Page, PlacedConnectorBox]],
    where: Mapping[Id[Any], Mapping[Page, PlacedFunction]],
    top: frozenset[Id[Any]],
) -> Spots:
    """The corner `end` is drawn at, by page: its plug's box, a top sheet's mate box, or a pin.

    Derive's `_line_stub_far` reads the same ends from the records; the lowest page wins there.
    """
    if end.plug is not None:
        at_box: Spots = {
            page: (one.box.x, one.box.y) for page, one in boxes.get(end.plug, {}).items()
        }
        if end.mates in top:
            mate = boxes.get(end.mates, {})
            at_box |= {
                page: (one.box.x, one.box.y) for page, one in mate.items() if page not in at_box
            }
        return at_box
    found: Spots = {}
    for function in {ports(model)[port].function for port in end.ports}:
        for page, one in where.get(function, {}).items():
            found[page] = min(found.get(page, (one.at.x, one.at.y)), (one.at.x, one.at.y))
    return found


class _Facts(Protocol):
    @property
    def boxes(self) -> Mapping[Id[Any], Mapping[Page, PlacedConnectorBox]]: ...
    @property
    def where(self) -> Mapping[Id[Any], Mapping[Page, PlacedFunction]]: ...
    @property
    def top(self) -> frozenset[Id[Any]]: ...


def line_spots(model: Model, lines: LineReads, world: _Facts) -> dict[tuple[Id[Any], int], Spots]:
    """Where each end of each line is drawn, by page, for the stubs' texts."""
    return {
        (line.owner, end.branch): end_spots(model, end, world.boxes, world.where, world.top)
        for line in lines.lines
        for end in line.ends
    }
