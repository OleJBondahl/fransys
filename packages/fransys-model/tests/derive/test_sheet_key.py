"""`SheetKey` and `sheet_key_text`: one page background's key and its printed form (pdf-0050)."""

import pytest

from fransys_model.derive import SheetKey, sheet_key_text
from fransys_model.kernel import Id, make_id, render_id
from fransys_model.vocab import Document, PageKind

_DOCUMENTS = (make_id(Document, ("document", "a")), make_id(Document, ("document", "b")))
_ORDINALS = (0, 1, 12, None)


def _old_text(document: Id[Document], kind: PageKind, index: int | None) -> str:
    """The text `derive.sheet_key` returned before the row: `none` for a missing ordinal."""
    return f"{render_id(document)}#{kind.name}#{'none' if index is None else index}"


@pytest.mark.parametrize("document", _DOCUMENTS)
@pytest.mark.parametrize("kind", list(PageKind))
@pytest.mark.parametrize("ordinal", _ORDINALS)
def test_text_is_the_old_sheet_key_text(document, kind, ordinal) -> None:
    assert sheet_key_text(SheetKey(document, kind, ordinal)) == _old_text(document, kind, ordinal)


def test_two_documents_give_two_hashable_keys() -> None:
    a, b = (SheetKey(d, PageKind.COVER, 0) for d in _DOCUMENTS)
    assert a != b
    assert len({a, b, SheetKey(_DOCUMENTS[0], PageKind.COVER, 0)}) == 2
