"""The contact tables a built model's core drawings hold: one door for the field cases (DEL-4).

A table is a `contact-head` symbol whose `texts` are a heading row (NO, NC) and then one row per
printed entry pair, an empty string for a column with no entry.
"""

import dataclasses
from typing import TYPE_CHECKING

from _drawn_extent import Rect, body_g
from _drawn_pages import drawn_pages
from symdef import Orientation

if TYPE_CHECKING:
    from fransys_layout.drawing import DrawnSymbol
    from fransys_model.kernel import Model

TABLE = "contact-head"


def table_symbols(model: Model) -> list[DrawnSymbol]:
    """Every contact table symbol of every page, pages in print order."""
    return [s for drawing in drawn_pages(model).values() for s in drawing.symbols if s.key == TABLE]


def entries(table: DrawnSymbol) -> tuple[list[str], list[str]]:
    """The NO and NC entries of `table` as it prints them, the heading row left out."""
    rows = table.texts[1:]
    return [r[0] for r in rows if r[0]], [r[1] for r in rows if r[1]]


def contact_table(model: Model) -> tuple[list[str], list[str]]:
    """The NO and NC entries of the one contact table of `model`."""
    (table,) = table_symbols(model)
    return entries(table)


def table_body_g(symbol: DrawnSymbol) -> Rect:
    """`body_g` of a drawn symbol whose orient is the string a Drawing holds, turned to symdef's."""
    return body_g(dataclasses.replace(symbol, orient=Orientation(symbol.orient)))
