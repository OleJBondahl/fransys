"""Reading the laid-out model for the readability report: page homes, and the finished rows."""

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from fransys_model.derive import (
    PageWires,
    ReadabilityPage,
    ReadabilityReport,
    page_wires,
    readability_units,
)
from fransys_model.layout import DrawingSet, Page, layout_of

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.kernel import Id, Model


def has_pages(model: Model) -> bool:
    """Whether `model` holds any laid-out page."""
    return bool(layout_of(model, Page))


def page_homes(laid: Model) -> dict[tuple[int, int], tuple[Id[Any], Id[Any] | None]]:
    """The `Page` id and the unit of each page of `laid`, by its `(drawing set, page)` numbers."""
    sets = layout_of(laid, DrawingSet)
    return {
        (sets[page.drawing_set].number, page.number): (page.id, sets[page.drawing_set].unit)
        for page in layout_of(laid, Page).values()
    }


def report_rows(
    model: Model, counts: Mapping[Id[Any], Mapping[str, Any]], leads: Mapping[Id[Any], int]
) -> tuple[ReadabilityPage, ...]:
    """A `ReadabilityPage` for each page of `model` with `counts`, by drawing set and page.

    The wire counts come from the model's lines and the `leads`, the power leads' grids by page.
    """
    sets = layout_of(model, DrawingSet)
    ordered = sorted(
        (page for page in layout_of(model, Page).values() if page.id in counts),
        key=lambda page: (sets[page.drawing_set].number, page.number),
    )
    wires = page_wires(model, leads)
    none = PageWires(bends=0, length_mm=Decimal(0))
    return tuple(
        ReadabilityPage(
            page=page.id,
            unit=sets[page.drawing_set].unit,
            drawing_set=sets[page.drawing_set].number,
            number=page.number,
            wire_bends=wires.get(page.id, none).bends,
            wire_length_mm=wires.get(page.id, none).length_mm,
            **counts[page.id],
        )
        for page in ordered
    )


def readability_report(
    model: Model,
    counts: Mapping[Id[Any], Mapping[str, Any]],
    loose: Mapping[Id[Any] | None, int],
    leads: Mapping[Id[Any], int],
) -> ReadabilityReport:
    """The report: the page rows of `counts`, a row per unit with its `loose` symbols, their sum."""
    pages = report_rows(model, counts, leads)
    return ReadabilityReport(
        pages=pages, units=readability_units(pages, loose), loose_symbols=sum(loose.values())
    )
