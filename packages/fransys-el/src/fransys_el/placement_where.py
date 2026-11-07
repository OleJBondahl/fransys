"""The room a terminal's where-text takes under its tag, reserved before any page exists (R1397).

A terminal placed more than once prints, under its tag, one line per other placement. The pages are
unknown when the tag is measured, so a terminal in two or more scopes reserves the widest position text once per other scope (KI-541).
"""

from typing import TYPE_CHECKING

from fransys_model.derive import function_role, function_scopes, widest_position_text
from fransys_model.layout import sheet_for
from fransys_model.vocab import PageKind

from .placement_widest import widest_digit

if TYPE_CHECKING:
    from electrical_symbols import Library
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Function

    from .placement_env import Env

__all__ = ["where_line", "where_room"]


def where_line(model: Model, library: Library, count: int) -> str:
    """The widest position text of a build of `count` symbols: one value per build, read by `where_room`."""
    sheets = [sheet_for(model, kind) for kind in PageKind]
    columns, rows = max(s.frame_columns for s in sheets), max(s.frame_rows for s in sheets)
    sample = len(widest_position_text(model, count, columns, rows, "1"))
    return widest_position_text(model, count, columns, rows, widest_digit(library, sample))


def where_room(env: Env, function: Id[Function]) -> str:
    """The lines a terminal's tag slot is measured with: a newline and the widest position text per other scope; empty for any other function."""
    if not function_role(env.model, function).terminal:
        return ""
    others = len(function_scopes(env.model, function)) - 1
    return ("\n" + env.where) * others if others >= 1 else ""
