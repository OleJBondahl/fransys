"""The one guard of a designation read before the numbering pass: empty text when it refuses."""

from typing import TYPE_CHECKING, Any

from fransys_model.kernel import SchemaError

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_model.kernel import Id, Model


def text_or_empty(text_of: Callable[[Model, Any], str], model: Model, ident: Id[Any]) -> str:
    """`text_of(model, ident)`, or "" when the model has no such text yet (before numbering)."""
    try:
        return text_of(model, ident)
    except SchemaError:
        return ""
