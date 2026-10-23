"""The text of a terminal, connector pin or port named on its own (design 7.7)."""

from fransys_model.derive.designation import terminal_of_item
lazy from fransys_model.derive.texts.context import PrintContext
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item


def terminal_text(model: Model, item: Id[Item], ctx: PrintContext) -> str:
    """Render `item` as a terminal, connector pin or port named on its own (`-X1:L1:1`).

    Always a leading `-`; under a strip `-<strip label>:<group:index>`, parentless `-<own label>`.
    The one terminal text; `terminal_of_item` is its body, kept in `designation` against a cycle.
    """
    return terminal_of_item(model, item, ctx.reading)
