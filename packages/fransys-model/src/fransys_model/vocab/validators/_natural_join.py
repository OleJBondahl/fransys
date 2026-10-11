"""One message join for the validators: texts in natural order, `-X2` before `-X10` (O8)."""

from typing import TYPE_CHECKING

from fransys_model.vocab.markings import marking_key

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = ["natural_join"]


def natural_join(texts: Iterable[str]) -> str:
    """The texts joined with `, `, digit runs ordered by value; the text breaks a tie."""
    ordered: list[str] = sorted(texts, key=lambda text: (marking_key(text), text))
    return ", ".join(ordered)
