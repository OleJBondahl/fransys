"""The overview engine: one pass from a model to its overview position records."""

from typing import Any

from fransys_layout.engines.overview.defaults import ENGINE_NAME, ENGINE_VERSION, PACK_SHAPE
from fransys_layout.engines.overview.place import place_view, view_findings, view_scene
from fransys_layout.engines.overview.read import read_views
from fransys_layout.engines.overview.write import view_records, write_overview
from fransys_layout.lint.codes import OVERVIEW_UNPLACED
from fransys_model.kernel import Finding, Id, Model, Severity


def _unplaced(first: Id[Any]) -> Finding:
    return Finding(
        code=OVERVIEW_UNPLACED,
        severity=Severity.ERROR,
        subjects=(first,),
        message="An overview view cannot be placed, so the page has no positions for it.",
    )


def lay_out_overview(model: Model) -> tuple[Model, tuple[Finding, ...]]:
    """Return `model` with the records of every overview view, and the lint findings.

    Pure. Every level, every opened unit and every open strip is placed with no sheet cut. A view
    the placer cannot place gets no records and an ERROR finding; the four diagram checks run on
    each placed view and their findings are ERRORs.
    """
    stamp = f"fransys-layout/{ENGINE_NAME} {ENGINE_VERSION}"
    records: list[object] = []
    found: list[Finding] = []
    for facts in read_views(model):
        sheet = place_view(facts, PACK_SHAPE)
        if sheet is None:
            found.append(_unplaced(facts.boxes[0].box))
            continue
        scene = view_scene(facts, sheet)
        found.extend(view_findings(scene))
        records.extend(view_records(facts, sheet, scene, stamp))
    ordered = tuple(sorted(found, key=lambda x: (x.code, x.subjects)))
    return write_overview(model, tuple(records)), ordered
