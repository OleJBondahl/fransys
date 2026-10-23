"""`write_layout_drawn`: `write_layout` plus the set's page drawings, from the same layout (F7).

The model is written exactly as `write_layout` writes it. The drawings are built beside it from
the layout and the pages that write produced, read back by number from the drawing set.
"""

from typing import TYPE_CHECKING

from fransys_model.layout import Page, layout_of

from .draw_layout import draw_set
from .drawn_identity import ports_of
from .drawn_texts import box_rows
from .placement_ids import symbol_key
from .write import _ORIGIN, _STAMP, write_layout
from .write_markers import link_markers
from .write_markings import marking_slots
from .write_pages import SetPlace, drawing_set
from .write_texts import symbol_keys

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


def write_layout_drawn(  # noqa: PLR0913 - `write_layout`'s inputs
    model: Model,
    unit: Id[Unit] | None,
    layout: CoreLayout,
    problem: PlacementProblem,
    kit: SymbolKit,
    *,
    library: Library,
    where: SetPlace | None = None,
) -> tuple[Model, tuple[Finding, ...], dict[Id[Page], Drawing], tuple[LinkMarker, ...]]:
    """`write_layout`'s model and findings; the set's drawings without markers; its markers.

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
    owner = drawing_set(unit, _STAMP, where).id
    pages = {p.number: p for p in layout_of(laid, Page).values() if p.drawing_set == owner}
    ports = ports_of(model, kit)
    shown = {
        (sym := symbol_key(model, f)): (pick.key, box_rows(pick), pick.poles, ports.get(sym, ()))
        for f, pick in kit.items()
    }
    marks = {symbol_key(model, f): marking_slots(model, pick, library) for f, pick in kit.items()}
    drawn = draw_set(
        model,
        layout,
        problem,
        kit,
        pages,
        number=where.number,
        shown=shown,
        marks=marks,
        keys=symbol_keys(model, kit),
        unit=unit,
    )
    markers = link_markers(
        layout, model, kit, pages, stamp=_STAMP, library=library, number=where.number, unit=unit
    )
    return laid, found, drawn, markers
