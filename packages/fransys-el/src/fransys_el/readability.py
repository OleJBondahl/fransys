"""`readability(drawings)`: the counts of how readable the drawn pages are (el-0043, R218)."""

from typing import TYPE_CHECKING

from fransys_layout.drawing import (
    page_texts,
    struck_texts,
    text_overlaps,
    wire_bends,
    wire_crossings,
    wire_length,
)
from fransys_model.derive import DrawnPageReading, DrawnReading

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.drawing import Drawing
    from fransys_model.kernel import Id
    from fransys_model.layout import Page

__all__ = ["readability"]


def _reading(page: Id[Page], drawing: Drawing) -> DrawnPageReading:
    """The counts of one page; its membership is what the `Drawing` carries."""
    texts = page_texts(drawing)
    return DrawnPageReading(
        page=page,
        symbols=len(drawing.symbols),
        markers=len(drawing.markers),
        wire_crossings=wire_crossings(drawing.wires),
        wire_bends=wire_bends(drawing.wires),
        wire_length_g=wire_length(drawing.wires),
        struck_labels=struck_texts(drawing.wires, texts),
        text_overlaps=text_overlaps(texts),
    )


def readability(drawings: Mapping[Id[Page], Drawing]) -> DrawnReading:
    """One reading for each page of `drawings`, in their order; no drawings give no pages.

    A count whose fact a `Drawing` does not carry is not in the reading (R168): the unit, the
    printed numbers, the text height, the fill, lone cells, contact images, stars and loose symbols.
    Pure: the same drawings give the same reading.
    """
    return DrawnReading(pages=tuple(_reading(page, drawing) for page, drawing in drawings.items()))
