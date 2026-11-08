"""`write_layout_drawn`: `write_layout` plus the set's page drawings, from the same layout (F7).

The model is written exactly as `write_layout` writes it. The drawings are built beside it from
the layout and the pages that write produced, read back by number from the drawing set.
"""

from typing import TYPE_CHECKING

from fransys_model.derive import refuses
from fransys_model.layout import Page, layout_of

from .draw_layout import draw_set
from .write import _ORIGIN, write_layout
from .write_markers import link_markers
from .write_pages import SetPlace, Written, drawing_set

if TYPE_CHECKING:
    from electrical_symbols import Library
    from fransys_layout.core import CoreLayout, PlacementProblem
    from fransys_layout.drawing import Drawing
    from fransys_model.kernel import Finding, Id, Model
    from fransys_model.layout import LinkMarker
    from fransys_model.vocab import Unit

    from .placement_kit import SymbolKit

__all__ = ["ORIGIN", "write_layout_drawn"]

ORIGIN = _ORIGIN


def write_layout_drawn(  # noqa: PLR0913 - `write_layout`'s inputs [internal builder of a public call, kept by decision 0414, KI-044]
    model: Model,
    unit: Id[Unit] | None,
    layout: CoreLayout,
    problem: PlacementProblem,
    kit: SymbolKit,
    *,
    library: Library,
    where: SetPlace | None = None,
) -> tuple[Model, tuple[Finding, ...], dict[Id[Page], Drawing], tuple[LinkMarker, ...], bool]:
    """`write_layout`'s model and findings; the set's drawings without markers; its markers; whether the output steps were skipped.

    Finish them with `draw_layout.finish_drawings` once every set is written.
    """
    where = where or SetPlace()
    laid, found = write_layout(
        model,
        unit,
        layout,
        problem,
        kit,
        library=library,
        where=where,
    )
    if refuses(found):
        return laid, found, {}, (), True  # the layout's ERROR stops the build before any drawing (KI-773)
    owner = drawing_set(unit, where)
    pages = {p.number: p for p in layout_of(laid, Page).values() if p.drawing_set == owner.id}
    written = Written(model, layout, problem, kit, library, pages, owner, unit)
    return laid, found, draw_set(written), link_markers(written), False
