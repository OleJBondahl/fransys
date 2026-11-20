"""The room a terminal's where-text takes under its tag, reserved before any page exists (R1397, R1883).

A terminal placed more than once prints, under its tag, one line per other placement. The pages are
unknown when the tag is measured, so a terminal in two or more scopes reserves, once per other scope, its own widest position text:
the far form (the printing document's prefix) for a placement in another PDF, the highest frame cell
of the formats and a page number of `digits` digits (KI-541).
"""

from typing import TYPE_CHECKING

from fransys_layout.symbols import text_width_g
from fransys_model.derive import function_abroad, function_role, function_scopes, position_room, printing_document
from fransys_model.layout import sheet_for
from fransys_model.vocab import PageKind

from .placement_widest import widest_digit

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_model.kernel import Id
    from fransys_model.vocab import Document, Function

    from .placement_env import Env

__all__ = ["where_room"]


def _width(env: Env, text: str) -> int:
    return text_width_g(env.library.font, text, height=env.conventions.text_height)


def _widest_line(env: Env, digits: int, frame: tuple[int, int], digit: str, far: Sequence[Id[Document]]) -> str:
    """The position text symdef measures widest over every frame row and every far document: a width, never a character count (TP7)."""
    lines = (
        position_room(env.model, digits, (frame[0], rows), digit, far=docs) for rows in range(1, frame[1] + 1) for docs in [[d] for d in far] or [far]
    )
    by_width = {_width(env, text): text for text in lines}
    return by_width[max(by_width)]


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
    sample = len(position_room(env.model, digits, frame, "1", far=far))
    return ("\n" + _widest_line(env, digits, frame, widest_digit(env.library, sample), far)) * others
