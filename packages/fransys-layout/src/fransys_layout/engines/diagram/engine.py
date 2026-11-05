"""The diagram engine: one pass from a model to its placed block diagrams."""

from fransys_layout.engines.diagram.read import read_diagrams, read_findings
from fransys_layout.engines.diagram.values import DiagramLayout
from fransys_layout.engines.overview.compose import place_diagram
from fransys_layout.engines.overview.scene import scene_of
from fransys_layout.lint import lint_diagram
lazy from fransys_layout.symbols import SymbolLibrary
lazy from fransys_model.kernel import Finding, Model


def lay_out_diagrams(model: Model, library: SymbolLibrary) -> tuple[DiagramLayout, tuple[Finding, ...]]:
    """Return the placed diagram of every reading, and the lint and read findings.

    Pure. A reading that cannot be placed is absent; the lint findings are ERRORs.
    """
    facts = read_diagrams(model, library)
    placed = [(f, place_diagram(f)) for f in facts]
    drawn = [(f, p) for f, p in placed if p is not None]
    lint = [lint_diagram(scene_of(f, s)) for f, p in drawn for s in p.sheets]
    found = (*(x for part in lint for x in part), *read_findings(model))
    ordered = tuple(sorted(found, key=lambda x: (x.code, x.subjects)))
    return DiagramLayout(diagrams=tuple(p for _, p in drawn)), ordered
