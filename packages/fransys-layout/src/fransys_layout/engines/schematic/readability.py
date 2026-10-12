"""The page rows of `fr.readability`: the engine run again on a laid-out model, then measured.

The model keeps no label boxes, keep-outs or marker stubs, so the counts of text struck by a wire,
of overlaps and of lone cells cannot be read from it. They are the lint's own functions
(`geometry_by_page`, `lone_cells`, `fill_shares`) run on the `Layout` of the same pure call
`build` makes (readability R11). Nothing is stored and no record changes.
"""

from collections import Counter
from typing import TYPE_CHECKING, Any

from fransys_layout.lint import fill_shares, geometry_by_page, lone_cells
from fransys_layout.lint.codes import TEXT_OVERLAP, WIRE_OVER_LABEL
from fransys_layout.lint.page_counts import reference_counts, wire_crossings
from fransys_layout.stages.slices import by_key, page_of

from ._lint import chain_records
from .engine import stage_scene
from .profiles import run_profiles
from .read import read_inputs
from .read.report import has_pages, page_homes, report_rows
from .read.sheets import printed_text
from .read.write_keys import write_keys
from .write import write_layout

if TYPE_CHECKING:
    from decimal import Decimal

    from fransys_model.kernel import Id, Model

    from ._lint import LintScene
    from .read.report import ReadabilityPage

type Measures = dict[Id[Any], tuple[Id[Any] | None, dict[str, Any]]]


def _measures(scene: LintScene, laid: Model, printed: tuple[Decimal, Decimal]) -> Measures:
    """The unit and the row counts of every placed page of one run, by its `Page` id."""
    layout, sheet = scene.layout, scene.inputs.sheet
    fill = fill_shares(layout, sheet=sheet)
    found = Counter(
        (here, f.code) for here, f in geometry_by_page(layout, sheet=sheet, ink=scene.ink)
    )
    lone = Counter(
        here for here, _ in lone_cells(layout, chain_records(scene), open_ends=scene.open_ends)
    )
    routes, labels, markers = (
        by_key(layout.routes, page_of),
        by_key(layout.labels, page_of),
        by_key(layout.markers, page_of),
    )
    homes = page_homes(laid)
    refs = {here: reference_counts(labels.get(here, ()), markers.get(here, ())) for here in fill}
    return {
        homes[here][0]: (
            homes[here][1],
            {
                "text_mm": printed[0],
                "min_text_mm": printed[1],
                "fill_percent": int(share * 100),
                "wire_crossings": wire_crossings(routes.get(here, ())),
                "struck_labels": found[here, WIRE_OVER_LABEL],
                "text_overlaps": found[here, TEXT_OVERLAP],
                "lone_cells": lone[here],
                "contact_images": refs[here].contact_images,
                "contact_image_targets": refs[here].contact_image_targets,
                "single_contact_images": refs[here].single_contact_images,
                "stars": refs[here].stars,
                "star_branches": refs[here].star_branches,
                "single_branch_stars": refs[here].single_branch_stars,
                "page_cuts": refs[here].page_cuts,
            },
        )
        for here, share in fill.items()
    }


def _measured_once(model: Model, unit: Id[Any] | None) -> tuple[Model, Measures]:
    """The engine's `_run_once`, which hands back what it measured in place of its findings."""
    results, scene, _ = stage_scene(model, inputs := read_inputs(model, unit))
    laid = write_layout(model, results, write_keys(model, inputs.functions))
    return laid, _measures(scene, laid, printed_text(model, unit))


def page_readability(model: Model) -> tuple[ReadabilityPage, ...]:
    """One `ReadabilityPage` per schematic page of `model`, in drawing set and page order.

    `model` is laid out: its `layout.page` records give each page its printed numbers. The engine
    runs once per layout profile in use, each unit's pages measured by the run of its own profile.
    """
    if not has_pages(model):
        return ()
    (_, base), runs = run_profiles(model, _measured_once)
    owned = {page: counts for page, (_, counts) in base.items()}
    for units, (_, measured) in runs:
        owned.update({page: counts for page, (unit, counts) in measured.items() if unit in units})
    return report_rows(model, owned)
