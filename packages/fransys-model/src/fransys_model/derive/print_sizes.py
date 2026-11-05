"""The one table of printed sizes, in mm (EXACT-SIZES E3, E4, E7, E10).

Reached as `fransys_model.derive.print_sizes.<name>`, never re-exported from `derive/__init__.py`.
A text size is a capital height (ISO 3098's h); `font_size_mm` looks up its font size in the
model's `DrawingLibrary` record (GRID-HOME G6), where the facade wrote symdef's em of every
height the build uses (`capital_heights`), so no package keeps a ratio or a role height of its own.
"""

from enum import Enum
from typing import TYPE_CHECKING
lazy from decimal import Decimal

from fransys_model.derive.library_grid import library_grid
from fransys_model.kernel import SchemaError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.kernel import Model

__all__ = [
    "TextRole",
    "ascent_ratio",
    "capital_heights",
    "font_size_mm",
    "height_key",
    "role_height_mm",
    "rule_mm",
]


class TextRole(Enum):
    """The four text roles of E3: a drawing label or table cell, body, heading 2, heading 1."""

    LABEL = "label"
    BODY = "body"
    HEADING_2 = "heading-2"
    HEADING_1 = "heading-1"


# The library height each role prints at; the heights themselves are the record's.
_ROLE_HEIGHT_NAME = {
    TextRole.LABEL: "smallest",
    TextRole.BODY: "body",
    TextRole.HEADING_2: "heading_2",
    TextRole.HEADING_1: "heading_1",
}


def height_key(capital_height_mm: Decimal) -> str:
    """The record key of a capital height: its canonical string, `1.8` or `5`."""
    return format(capital_height_mm.normalize(), "f")


def font_size_mm(model: Model, capital_height_mm: Decimal) -> Decimal:
    """The font size, in mm, whose capitals are `capital_height_mm` high: symdef's em, looked up.

    The facade wrote the em of every height `capital_heights` lists; any other height raises.
    """
    ems = library_grid(model).ems
    key = height_key(capital_height_mm)
    if key not in ems:
        msg = f"no font size for a capital height of {key} mm: the build's drawing library holds {', '.join(ems)}. Set the height in [font.heights]"
        raise SchemaError(msg, kind="layout.drawing_library")
    return ems[key]


def rule_mm(model: Model) -> Decimal:
    """The table rule's stroke width in mm, from the build's library lines."""
    return library_grid(model).lines["rule"]


def ascent_ratio(model: Model) -> Decimal:
    """How far the font's ascent reaches above the baseline per font size."""
    return library_grid(model).ascent_ratio


def role_height_mm(model: Model, role: TextRole) -> Decimal:
    """The capital height, in mm, that text of `role` prints at: the build's library height (E10).

    The smallest library height is the smallest text on every page kind; a label prints at it.
    """
    return library_grid(model).heights[_ROLE_HEIGHT_NAME[role]]


def capital_heights(role_heights: Mapping[str, Decimal]) -> tuple[Decimal, ...]:
    """Every capital height the build prints at, once each, in the library's order.

    The facade writes symdef's em of each into the record; this reads no record, so it can run
    before the record exists.
    """
    return tuple(dict.fromkeys(role_heights.values()))
