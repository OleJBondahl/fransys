"""The house words and revision settings a pdf prints, as plain values for `fransys_pdf.source`.

The pdf reads no record: the facade passes these, resolved from the model's `[words]` and
`[revision_table]` records.
"""

lazy from fransys_model.kernel import Model

from .facts.house_settings import revision_table_form_of, word
from .rows_pdf_texts import PdfTexts

__all__ = ["pdf_texts"]

_WORDS = ("notes", "sheet", "title", "page", "bridge")


def pdf_texts(model: Model) -> PdfTexts:
    """The keyword values of `fransys_pdf.source` that come from the house text records."""
    table = revision_table_form_of(model)
    revision_headers = tuple(word(model, key) for key in table.columns)
    return PdfTexts(
        words={key: word(model, key) for key in _WORDS},
        revision_headers=revision_headers,
        description_mm=float(table.description_mm),
    )
