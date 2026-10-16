"""The diagram engine: one pass from a model to its block diagram records."""

from fransys_layout.engines.diagram.read import read_diagrams, read_findings
from fransys_layout.engines.diagram.read.findings import too_tall_finding
from fransys_layout.engines.diagram.write import write_diagrams
from fransys_layout.engines.overview.compose import place_diagram
from fransys_layout.engines.overview.lanes.diagram_frame import tall_column
from fransys_layout.engines.overview.scene import scene_of
from fransys_layout.lint import lint_diagram
lazy from fransys_model.kernel import Finding, Model


def lay_out_diagrams(model: Model) -> tuple[Model, tuple[Finding, ...]]:
    """Return `model` with the records of every reading's diagram, and the lint and read findings.

    Pure. A reading that cannot be placed gets no records; the lint findings are ERRORs.
    """
    facts = read_diagrams(model)
    placed = [(f, place_diagram(f)) for f in facts]
    drawn = [(f, p) for f, p in placed if p is not None]
    lint = [lint_diagram(scene_of(f, s)) for f, p in drawn for s in p.sheets]
    tall = [(f, tall_column(f)) for f, p in placed if p is None]
    details = [too_tall_finding(f.unit, f.lines[0].cable, *t) for f, t in tall if t is not None]
    found = (*(x for part in lint for x in part), *read_findings(model), *details)
    ordered = tuple(sorted(found, key=lambda x: (x.code, x.subjects)))
    return write_diagrams(model, tuple(p for _, p in drawn)), ordered
