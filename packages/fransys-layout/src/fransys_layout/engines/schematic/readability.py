"""The page rows of `fr.readability`: the engine run again on a laid-out model, then measured.

The model keeps no label boxes, keep-outs or marker stubs, so the counts of text struck by a wire,
of overlaps and of lone cells cannot be read from it. They are the lint's own functions
(`geometry_by_page`, `lone_cells`, `fill_shares`) run on the `Layout` of the same pure call
`build` makes (readability R11). Nothing is stored and no record changes.
"""

from collections import Counter
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import WIRING_GRID
from fransys_layout.lint import fill_shares, geometry_by_page, lone_cells
from fransys_layout.lint.codes import TEXT_OVERLAP, WIRE_OVER_LABEL
from fransys_layout.lint.page_counts import reference_counts, wire_crossings
from fransys_layout.lint.printed import on_printed
from fransys_layout.stages.slices import by_key, page_of
from fransys_layout.stages.texts.power import power_places

from ._lint import chain_records
from .engine import stage_scene
from .profiles import run_profiles
from .read import read_inputs
from .read.printed import printed_set_numbers
from .read.report import has_pages, page_homes, readability_report
from .read.sheets import printed_text
from .read.units import item_unit
from .read.write_keys import write_keys
from .write import write_layout

if TYPE_CHECKING:
    from decimal import Decimal

    from fransys_layout.options import LayoutOptions
    from fransys_layout.stages.line_shapes import DrawnFanOut, DrawnLine
    from fransys_model.kernel import Id, Model

    from ._lint import LintScene
    from .read.report import ReadabilityReport

type Measures = dict[Id[Any], tuple[Id[Any] | None, dict[str, Any]]]


def _ink_page(one: DrawnLine | DrawnFanOut) -> tuple[int, int]:
    return one.drawing_set, one.page


def _measures(
    scene: LintScene, laid: Model, text: tuple[Decimal, Decimal], printed: frozenset[int] | None
) -> Measures:
    """The unit and the row counts of every page of one run in a printed set, by its `Page` id."""
    layout, sheet = scene.layout, scene.inputs.sheet
    fill = fill_shares(layout, sheet=sheet, ink=scene.ink)
    found = Counter(
        (here, f.code) for here, f in geometry_by_page(layout, sheet=sheet, ink=scene.ink)
    )
    lone = Counter(here for here, _ in lone_cells(layout, chain_records(scene)))
    routes, labels, markers = (
        by_key(layout.routes, page_of),
        by_key(layout.labels, page_of),
        by_key(layout.markers, page_of),
    )
    lines, fans = by_key(scene.ink.lines, _ink_page), by_key(scene.ink.fan_outs, _ink_page)
    homes = page_homes(laid)
    refs = {here: reference_counts(labels.get(here, ()), markers.get(here, ())) for here in fill}
    return {
        homes[here][0]: (
            homes[here][1],
            {
                "text_height_mm": text[0],
                "min_text_height_mm": text[1],
                "fill_percent": int(share * 100),
                "wire_crossings": wire_crossings(
                    routes.get(here, ()), lines.get(here, ()), fans.get(here, ())
                ),
                "struck_labels": found[here, WIRE_OVER_LABEL],
                "text_overlaps": found[here, TEXT_OVERLAP],
                "lone_cells": lone[here],
                "contact_images": refs[here].contact_images,
                "contact_image_targets": refs[here].contact_image_targets,
                "single_contact_images": refs[here].single_contact_images,
                "single_contact_images_other_page": refs[here].single_contact_images_other_page,
                "stars": refs[here].stars,
                "star_branches": refs[here].star_branches,
                "single_branch_stars": refs[here].single_branch_stars,
                "page_cuts": refs[here].page_cuts,
            },
        )
        for here, share in fill.items()
        if on_printed(here, printed)
    }


@dataclass(frozen=True, slots=True)
class _Measured:
    """What one run measured: the page rows' counts, the loose symbols by unit, the power leads.

    `leads` is the grids' length of the straight power leads of each measured page, by `Page` id.
    """

    measures: Measures
    loose: Counter[Id[Any] | None]
    leads: Counter[Id[Any]]


def _measured_once(
    model: Model, unit: Id[Any] | None, *, options: LayoutOptions
) -> tuple[Model, _Measured]:
    """The engine's `_run_once`, handing back what it measured instead of its findings."""
    results, scene, _ = stage_scene(model, inputs := read_inputs(model, unit, options=options))
    laid = write_layout(model, results, write_keys(model, inputs.functions))
    measures = _measures(scene, laid, printed_text(model, unit), printed_set_numbers(laid))
    homes = page_homes(laid)
    return laid, _Measured(
        measures=measures,
        loose=Counter(item_unit(model, s.item) for s in scene.inputs.loose),
        leads=Counter(
            {
                homes[place.drawing_set, place.page][0]: place.grids * WIRING_GRID
                for place in power_places(scene.layout.markers)
                if homes[place.drawing_set, place.page][0] in measures
            }
        ),
    )


def page_readability(model: Model, options: LayoutOptions) -> ReadabilityReport:
    """The `ReadabilityReport` of `model`: a row per schematic page, per unit, and the loose count.

    `model` is laid out: its `layout.page` records give each page its printed numbers. The engine
    runs once per layout profile in use, each unit's pages and loose symbols measured by the run of
    its own profile.
    """
    if not has_pages(model):
        return readability_report(model, {}, Counter(), Counter())
    (_, base), runs = run_profiles(model, partial(_measured_once, options=options))
    owned = {page: counts for page, (_, counts) in base.measures.items()}
    loose, leads = Counter(base.loose), Counter(base.leads)
    for units, (_, run) in runs:
        mine = {page: counts for page, (unit, counts) in run.measures.items() if unit in units}
        stale = {page for page, (unit, _) in base.measures.items() if unit in units} - mine.keys()
        owned = {page: counts for page, counts in owned.items() if page not in stale}
        leads = Counter({page: n for page, n in leads.items() if page not in stale})
        owned.update(mine)
        loose = Counter({u: n for u, n in loose.items() if u not in units})
        loose.update({u: n for u, n in run.loose.items() if u in units})
        leads.update({page: n for page, n in run.leads.items() if page in mine})
    return readability_report(model, owned, loose, leads)
