"""The diagram engine: one pass from a model to its block diagram records (BD5)."""

from fransys_layout.engines.diagram.place import place_diagram
from fransys_layout.engines.diagram.read import read_diagrams, read_findings
from fransys_layout.engines.diagram.scene import scene_of
from fransys_layout.engines.diagram.write import write_diagrams
from fransys_layout.lint import lint_diagram
lazy from fransys_model.kernel import Finding, Model


def lay_out_diagrams(model: Model) -> tuple[Model, tuple[Finding, ...]]:
    """Return `model` with the records of every reading's diagram, and the lint and read findings.

    Pure. A reading that cannot be placed gets no records; the lint findings are ERRORs (BD8).
    """
    facts = read_diagrams(model)
    placed = [(f, place_diagram(f)) for f in facts]
    drawn = [(f, p) for f, p in placed if p is not None]
    lint = [lint_diagram(scene_of(f, s)) for f, p in drawn for s in p.sheets]
    found = (*(x for part in lint for x in part), *read_findings(model))
    ordered = tuple(sorted(found, key=lambda x: (x.code, x.subjects)))
    return write_diagrams(model, tuple(p for _, p in drawn)), ordered
