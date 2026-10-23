"""The shape of the values `pdf_texts` hands to `fransys_pdf.source`."""

from typing import TypedDict

__all__ = ["PdfTexts"]


class PdfTexts(TypedDict):
    """The keyword values of `fransys_pdf.source` that come from the house text records."""

    words: dict[str, str]
    revision_headers: tuple[str, ...]
    description_mm: float
