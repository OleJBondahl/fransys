"""The one reader of the build's drawing library record: grid, font and text heights (G6).

`mm_per_division` is the one millimetre length of a grid unit; every conversion reads it. The
record is written by the facade, so a model that never went through it has none and raises.
"""

from decimal import Decimal

from fransys_model.kernel import SchemaError
from fransys_model.layout import DrawingLibrary, layout_of
lazy from fransys_model.kernel import Model
lazy from fransys_model.layout import SheetFormat

lazy from .rows_drawn_sheets import SheetRow

__all__ = [
    "descent_ratio",
    "divisions",
    "font_family",
    "library_grid",
    "mm_per_division",
    "text_height",
    "wire_pitch",
]


def library_grid(model: Model) -> DrawingLibrary:
    """The model's drawing library record; raises when the facade wrote none."""
    found = layout_of(model, DrawingLibrary)
    if not found:
        msg = "this model carries no drawing library record: build it through `fransys.build`"
        raise SchemaError(msg, kind="layout.drawing_library")
    return next(iter(found.values()))


def divisions(model: Model) -> int:
    """Grid divisions (`G`) in one module."""
    return library_grid(model).divisions


def mm_per_division(model: Model, sheet: SheetFormat | SheetRow) -> Decimal:
    """One grid division in millimetres: the sheet's module over the record's divisions.

    Until GRID-HOME-B the sheet still sets the module; then it reads the record alone.
    """
    return sheet.module_mm / Decimal(library_grid(model).divisions)


def text_height(model: Model, name: str) -> Decimal:
    """The library's capital height in mm for `name` (`smallest`, `body`, `heading_2`, ...)."""
    return library_grid(model).heights[name]


def wire_pitch(model: Model, *, fine: bool = False) -> int:
    """The wire pitch in grid divisions: the house pitch, or the fine one."""
    record = library_grid(model)
    return record.wire_pitch_fine if fine else record.wire_pitch


def font_family(model: Model) -> str:
    """The family name the drawings' text is set in."""
    return library_grid(model).font_family


def descent_ratio(model: Model) -> Decimal:
    """The descender depth over the font size."""
    return library_grid(model).descent_ratio
