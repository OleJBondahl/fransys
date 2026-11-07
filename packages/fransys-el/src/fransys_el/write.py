"""`write_layout`: a `CoreLayout` written into the model as `layout.*` records (el-0003, E2)."""

from typing import TYPE_CHECKING

from fransys_model.kernel import Origin, evolve

from .write_findings import kernel_findings
from .write_ids import group_ids, symbol_subjects
from .write_markers import link_markers
from .write_membership import memberships, set_rows
from .write_pages import STAMP, SetPlace, Written, write_pages
from .write_power import power_symbols

if TYPE_CHECKING:
    from electrical_symbols import Library
    from fransys_layout.core import CoreLayout, PlacementProblem
    from fransys_model.kernel import Finding, Id, Model
    from fransys_model.vocab import Unit

    from .placement_kit import SymbolKit

__all__ = ["write_layout"]

_ORIGIN = Origin(file="fransys_el/write.py", line=0, note="the placement core layout")


def write_layout(  # noqa: PLR0913 - the library and the place join the five inputs [public keyword API kept, decision 0444]
    model: Model,
    unit: Id[Unit] | None,
    layout: CoreLayout,
    problem: PlacementProblem,
    kit: SymbolKit,
    *,
    library: Library,
    where: SetPlace | None = None,
) -> tuple[Model, tuple[Finding, ...]]:
    """Write the pages, power symbols, markers and memberships of `layout`; map its findings.

    The symbol of a placed function is `kit[function].key`: the pick the facade made once, never
    made again here (el-0003). `unit` is the drawing set's unit, `None` for the whole design;
    `where` its location and number.
    `library` gives the markers their size.
    """
    sets, pages = write_pages(model, layout.pages, unit, group_ids(model), where)
    written = Written(model, layout, problem, kit, library, pages, sets[0], unit)
    records = (
        *sets,
        *pages.values(),
        *power_symbols(model, layout, pages, kit, (STAMP, sets[0].number)),
        *link_markers(written),
        *memberships(written),
    )
    own = set_rows(model, sets[0].number, STAMP)
    laid = evolve(model, put=records, remove=own, origin=_ORIGIN)
    return laid, kernel_findings(laid, layout.findings, symbol_subjects(model, kit), pages)
