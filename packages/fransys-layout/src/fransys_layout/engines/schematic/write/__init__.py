"""Schematic engine, writing: stage outputs to derived `layout.*` records (design/engine.md 7)."""

from typing import TYPE_CHECKING

from fransys_layout.engines.schematic.defaults import ENGINE_NAME, ENGINE_VERSION

# the builders `placements`, `routes` and `labels` are called through their modules: a module and
# its builder share a name, and the package attribute must stay the module
from fransys_layout.engines.schematic.write import harness, labels, placements, routes
from fransys_layout.engines.schematic.write.markers import link_markers
from fransys_layout.engines.schematic.write.power import power_symbols
from fransys_layout.engines.schematic.write.sets import drawing_sets, pages
from fransys_layout.engines.schematic.write.unique import check_unique
from fransys_model.kernel import Origin, evolve
from fransys_model.layout import derived_layout_ids

if TYPE_CHECKING:
    from fransys_layout.engines.schematic.engine import StageResults
    from fransys_layout.engines.schematic.write.keys import WriteKeys
    from fransys_model.kernel import Model


def produced_by() -> str:
    """Return `"fransys-layout/schematic <package version>"`, the stamp of every record."""
    return f"fransys-layout/{ENGINE_NAME} {ENGINE_VERSION}"


def write_layout(model: Model, results: StageResults, keys: WriteKeys) -> Model:
    """Replace every derived `layout.*` record of `model` with the ones `results` describe."""
    stamp = produced_by()
    layout = results.layout
    sets = drawing_sets(keys, layout.pages, stamp)
    page_of = pages(keys, layout.pages, sets, results.sheet_format, stamp)
    symbols, discriminator = placements.placements(keys, results, page_of, sets, stamp)
    records = [
        *sets.values(),
        *page_of.values(),
        *symbols,
        *routes.routes(keys, layout, page_of, stamp),
        *link_markers(keys, results, page_of, discriminator, stamp),
        *power_symbols(keys, results, page_of, discriminator, stamp),
        *labels.labels(keys, results, page_of, discriminator, stamp),
        *labels.outlines(keys, layout, page_of, discriminator, stamp),
        *harness.connector_boxes(keys, results.boxes, page_of, sets, stamp),
        *harness.harness_lines(keys, results.lines.lines, page_of, sets, stamp),
        *harness.harness_fan_outs(keys, results.lines.fan_outs, page_of, sets, stamp),
        *harness.line_stubs(keys, results.lines.stubs, page_of, sets, stamp),
    ]
    check_unique(keys, records, {page.id: sets[at[0]].key for at, page in page_of.items()})
    origin = Origin(file=stamp, line=1, note="derived layout record")
    return evolve(model, remove=derived_layout_ids(model), put=records, origin=origin)
