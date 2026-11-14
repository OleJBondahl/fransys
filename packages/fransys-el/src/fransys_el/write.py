"""`write_layout`: a `CoreLayout` written into the model as `layout.*` records (el-0003, E2)."""

from dataclasses import replace
from typing import TYPE_CHECKING

from fransys_model.derive import export_set_name, refuses
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


def _named_skip(found: Finding, name: str) -> Finding:
    """An ERROR names its drawing set (the printed set name) as not drawn and its drawn-page checks did not run."""
    return (
        replace(found, message=f"{found.message}; drawing set {name!r} is not drawn, its drawn-page checks did not run")
        if refuses((found,))
        else found
    )


def write_layout(  # noqa: PLR0913 - the library and the place join the five inputs [public keyword API kept, decision 0444]
    model: Model,
    unit: Id[Unit] | None,
    layout: CoreLayout,
    problem: PlacementProblem,
    kit: SymbolKit,
    *,
    library: Library,
    where: SetPlace | None = None,
) -> tuple[Model, tuple[Finding, ...], bool]:
    """Write the pages, power symbols, markers and memberships of `layout`; map its findings; say whether the output steps were skipped.

    A placed function's symbol is `kit[function].key`, the pick made once (el-0003).
    """
    sets, pages = write_pages(model, layout.pages, unit, group_ids(model), where)
    written = Written(model, layout, problem, kit, library, pages, sets[0], unit)
    own = set_rows(model, sets[0].number, STAMP)
    paged = evolve(model, put=(*sets, *pages.values()), remove=own, origin=_ORIGIN)
    found = kernel_findings(paged, layout.findings, symbol_subjects(model, kit), pages)
    if refuses(found):  # no output step runs for this set (KI-773, R1945); the other sets are checked (KI-779, R1978)
        return paged, tuple(_named_skip(f, export_set_name(model, unit)) for f in found), True
    records = (
        *power_symbols(model, layout, pages, kit, (STAMP, sets[0].number)),
        *link_markers(written),
        *memberships(written),
    )
    return evolve(paged, put=records, origin=_ORIGIN), found, False
