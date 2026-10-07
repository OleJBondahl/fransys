"""Diagram engine, writing: placed diagrams to derived `layout.diagram_*` records."""

from typing import TYPE_CHECKING

from fransys_layout.engines.diagram.defaults import ENGINE_NAME, ENGINE_VERSION
from fransys_layout.engines.diagram.write.records import sheet_records
from fransys_model.kernel import Origin, evolve
from fransys_model.layout import DIAGRAM_KINDS, derived_layout_ids

if TYPE_CHECKING:
    from fransys_layout.engines.diagram.values import PlacedDiagram
    from fransys_model.kernel import Model


def write_diagrams(model: Model, diagrams: tuple[PlacedDiagram, ...]) -> Model:
    """Replace every diagram-kind `layout.*` record of `model` with the ones `diagrams` describe."""
    stamp = f"fransys-layout/{ENGINE_NAME} {ENGINE_VERSION}"
    records = [
        record
        for diagram in diagrams
        for sheet in diagram.sheets
        for record in sheet_records(diagram.unit, sheet, stamp)
    ]
    origin = Origin(file=stamp, line=1, note="derived layout record")
    remove = derived_layout_ids(model, kinds=DIAGRAM_KINDS)
    return evolve(model, remove=remove, put=records, origin=origin)
