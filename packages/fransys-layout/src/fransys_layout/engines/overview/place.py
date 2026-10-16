"""One view's placement: the diagram placer with no sheet limit, then the shared lint."""

from fransys_layout.engines.overview.defaults import PACK_SHAPE
from fransys_layout.engines.overview.lanes import place_lanes
from fransys_layout.engines.overview.pieces import place_packed
from fransys_layout.engines.overview.scene import scene_of
from fransys_layout.lint import lint_diagram
lazy from fransys_layout.engines.overview.read.values import ViewFacts
lazy from fransys_layout.engines.overview.sheet_values import PlacedSheet
lazy from fransys_layout.lint._diagram_scene import Scene
lazy from fransys_model.kernel import Finding


def place_view(facts: ViewFacts, shape: tuple[int, int] = PACK_SHAPE) -> PlacedSheet | None:
    """The view's one sheet, its pieces packed to `shape`, or `None` when there is no room plan."""
    if facts.lanes:
        return place_lanes(facts)
    placed = place_packed(facts.diagram, shape)
    return placed.sheets[0] if placed is not None and len(placed.sheets) == 1 else None


def view_scene(facts: ViewFacts, sheet: PlacedSheet) -> Scene:
    """The lint scene of a placed view."""
    return scene_of(facts.diagram, sheet)


def view_findings(scene: Scene) -> tuple[Finding, ...]:
    """The four diagram checks on `scene`, sorted by code and subjects."""
    return lint_diagram(scene)
