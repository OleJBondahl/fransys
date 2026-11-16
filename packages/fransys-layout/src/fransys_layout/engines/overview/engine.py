"""The overview engine: one pass from a model to the placed overview."""

from typing import TYPE_CHECKING, Any

from fransys_layout.engines.overview.defaults import PACK_SHAPE
from fransys_layout.engines.overview.place import place_view, view_findings, view_scene
from fransys_layout.engines.overview.read import read_views
from fransys_layout.engines.overview.read.result import OverviewLayout, OverviewPlacedView, placed_view
from fransys_layout.fix_text import finding
from fransys_layout.lint.codes import OVERVIEW_UNPLACED

if TYPE_CHECKING:
    from fransys_layout.symbols import SymbolLibrary
    from fransys_model.kernel import Finding, Id, Model


def _unplaced(first: Id[Any]) -> Finding:
    return finding(
        OVERVIEW_UNPLACED,
        (first,),
        "An overview view cannot be placed, so the page has no positions for it.",
    )


def lay_out_overview(model: Model, library: SymbolLibrary) -> tuple[OverviewLayout, tuple[Finding, ...]]:
    """Return the placed overview of `model` and the lint findings.

    Pure. Every level, every opened unit and every open strip is placed with no sheet cut. A view
    the placer cannot place is absent and gets an ERROR finding; the four diagram checks run on
    each placed view and their findings are ERRORs.
    """
    views: list[OverviewPlacedView] = []
    found: list[Finding] = []
    for facts in read_views(model, library):
        sheet = place_view(facts, PACK_SHAPE)
        if sheet is None:
            found.append(_unplaced(facts.boxes[0].box))
            continue
        scene = view_scene(facts, sheet)
        found.extend(view_findings(scene))
        views.append(placed_view(facts, sheet, scene))
    ordered = tuple(sorted(found, key=lambda x: (x.code, x.subjects)))
    return OverviewLayout(views=tuple(views)), ordered
