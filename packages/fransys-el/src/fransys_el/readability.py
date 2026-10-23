"""`readability(drawings, units)`: how readable the drawn pages are in numbers (el-0043, R218)."""

from typing import TYPE_CHECKING

from fransys_layout.drawing import (
    fill_percent,
    page_texts,
    struck_texts,
    text_overlaps,
    wire_bends,
    wire_crossings,
    wire_length,
)
from fransys_model.derive import DrawnPageReading, DrawnReading

from .placement_views import MARKER_KEYS

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.drawing import Drawing
    from fransys_model.kernel import Id
    from fransys_model.layout import Page
    from fransys_model.vocab import Unit

__all__ = ["readability"]


def _reading(page: Id[Page], unit: Id[Unit] | None, drawing: Drawing) -> DrawnPageReading:
    """The counts of one page; its membership is what the `Drawing` carries."""
    texts = page_texts(drawing)
    return DrawnPageReading(
        page=page,
        unit=unit,
        symbols=len(drawing.symbols),
        markers=sum(symbol.key in MARKER_KEYS for symbol in drawing.symbols),
        fill_percent=fill_percent(drawing),
        wire_crossings=wire_crossings(drawing.wires),
        wire_bends=wire_bends(drawing.wires),
        wire_length_g=wire_length(drawing.wires),
        struck_labels=struck_texts(drawing.wires, texts),
        text_overlaps=text_overlaps(texts),
    )


def readability(
    drawings: Mapping[Id[Page], Drawing], units: Mapping[Id[Page], Id[Unit] | None]
) -> DrawnReading:
    """One reading for each page of `drawings`, in their order; no drawings give no pages.

    `units` gives each page its unit (`derive.set_unit` of its drawing set); a page it lacks has
    none. `markers` counts the reference markers in the total, as every kind draws the same symbol.
    A count whose fact a `Drawing` does not carry is not in the reading (R168): the printed numbers,
    lone cells, contact images, stars, page cuts, the text height and loose symbols.
    Pure: the same drawings give the same reading.
    """
    return DrawnReading(
        pages=tuple(_reading(page, units.get(page), drawing) for page, drawing in drawings.items())
    )
