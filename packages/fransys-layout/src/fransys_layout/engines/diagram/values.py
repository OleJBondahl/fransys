"""The diagram engine's result: every reading's placed diagram, as one value (layout-0409)."""

from fransys_layout.engines.overview.sheet_values import Ident, PlacedDiagram, PlacedSheet
from fransys_layout.geometry import LayoutError
from fransys_model.kernel import value


def _check_markers(sheet: PlacedSheet) -> None:
    """Refuse a sheet with a marker that has no line of the same cable and ends."""
    lines = {(line.cable, line.a, line.b) for line in sheet.lines}
    for marker in sheet.markers:
        if (marker.cable, marker.a, marker.b) not in lines:
            msg = f"sheet {sheet.number} has a marker with no line of the same cable and ends"
            raise LayoutError(msg)


@value
class DiagramLayout:
    """The placed diagram of each reading that could be drawn, in the engine's order.

    A reading that cannot be placed is absent. Every marker has a line of its cable and ends.
    """

    diagrams: tuple[PlacedDiagram, ...]

    def __post_init__(self) -> None:
        """Check every sheet's markers."""
        for diagram in self.diagrams:
            for sheet in diagram.sheets:
                _check_markers(sheet)

    def sheet_places(self) -> tuple[tuple[Ident | None, int], ...]:
        """`(reading, number)` of every sheet, in the engine's order."""
        return tuple((d.unit, s.number) for d in self.diagrams for s in d.sheets)
