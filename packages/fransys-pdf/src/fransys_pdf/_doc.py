"""One document's derive rows, built once by `source` and handed to every page builder."""

from typing import TYPE_CHECKING

from fransys_model.derive import SheetKey

from ._background import page_background

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.derive import BridgePieceRow, DiagramSheet, DocumentRow, SheetBackground, SheetRow
    from fransys_model.kernel import Model
    from fransys_model.vocab import PageKind

type BridgeInputs = tuple[str, Mapping[str, BridgePieceRow] | None, float]
"""The Bridge column's heading word, `fransys_render.bridge_pieces()` and the column width in mm."""
type Doc = tuple[
    Model, DocumentRow, tuple[PageKind, ...], SheetRow, Mapping[SheetKey, SheetBackground], tuple[DiagramSheet, ...], Mapping[str, float]
]
"""The model, the document's row, its page kinds, its paper, the page backgrounds, the placed diagram sheets and the `[pdf]` numbers."""


def background(doc: Doc, kind: PageKind, index: int | None) -> str:
    """The `#page` background of page `index` of `kind` (`None`: the one no-drawings page)."""
    model, record, _, _, sheets, _, _ = doc
    return page_background(model, record, sheets, SheetKey(record.id, kind, index))
