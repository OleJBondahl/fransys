"""The room a terminal's where-text takes under its tag, reserved before any page exists (R1397, R1883).

A terminal placed more than once prints, under its tag, one line per other placement. The pages are
unknown when the tag is measured, so a terminal in two or more scopes reserves, once per other scope, its own widest position text:
the far form (the printing document's prefix) for a placement in another PDF, the highest frame cell
of the formats and a page number of `digits` digits (KI-541).
"""

from typing import TYPE_CHECKING

from fransys_model.derive import function_abroad, function_role, function_scopes, printing_document, widest_position_text
from fransys_model.layout import sheet_for
from fransys_model.vocab import PageKind

from .placement_widest import widest_digit

if TYPE_CHECKING:
    from fransys_model.kernel import Id
    from fransys_model.vocab import Function

    from .placement_env import Env

__all__ = ["where_room"]


def where_room(env: Env, function: Id[Function], digits: int = 1) -> str:
    """The tag slot's extra lines: the widest position text of any scope, once per other scope; empty for any other function."""
    others = len(function_scopes(env.model, function)) - 1
    if others < 1 or not function_role(env.model, function).terminal:
        return ""
    sheets = [sheet_for(env.model, kind) for kind in PageKind]
    frame = (max(s.frame_columns for s in sheets), max(s.frame_rows for s in sheets))
    abroad = function_abroad(env.model, function)
    documents = (printing_document(env.model, *scope) for scope in function_scopes(env.model, function))
    far = [d for d in documents if d] if abroad else []  # a line may name any scope's document: each viewer sees the others as far
    sample = len(widest_position_text(env.model, digits, frame, "1", far=far))
    return ("\n" + widest_position_text(env.model, digits, frame, widest_digit(env.library, sample), far=far)) * others
