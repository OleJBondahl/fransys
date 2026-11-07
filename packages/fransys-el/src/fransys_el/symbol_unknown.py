"""`UNKNOWN_SYMBOL_KEY`: a function whose chosen symbol key the library lacks (el-0039, R242).

The kit draws such a function as a generic box, so the layout goes on; the finding names the
function and the page it stands on.
"""

from typing import TYPE_CHECKING

from electrical_symbols import GENERIC_BOX_KEY
from fransys_layout.core import CoreError
from fransys_layout.symbols import library_symbol
from fransys_model.derive import function_designation, page_reference_text
from fransys_model.layout import Membership, Page, layout_of
lazy from fransys_model.kernel import Finding

from .codes import FINDING_CODES

if TYPE_CHECKING:
    from electrical_symbols import Library
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Function

__all__ = ["unknown_symbol_key_findings"]

_INFO = next(info for info in FINDING_CODES if info.code == "UNKNOWN_SYMBOL_KEY")


def is_unknown(library: Library, key: str) -> bool:
    """Whether `key` names no symbol of `library`."""
    if key == GENERIC_BOX_KEY:  # the labelled box, chosen by its public key (R479)
        return False
    try:
        library_symbol(library, key)
    except CoreError:
        return True
    return False


def _page_of(model: Model, function: Id[Function]) -> Page | None:
    """The first page whose `Membership` shows `function`, or `None` when none does."""
    pages = layout_of(model, Page)
    return next((pages[row.page] for row in layout_of(model, Membership).values() if row.function == function and row.page is not None), None)


def unknown_symbol_key_findings(laid: Model, unknown: dict[Id[Function], str]) -> tuple[Finding, ...]:
    """One `UNKNOWN_SYMBOL_KEY` ERROR per function of `unknown` (to its key), read after layout."""
    found = []
    for function, key in unknown.items():
        page = _page_of(laid, function)
        where = "" if page is None else f"{page_reference_text(laid, page)}: "
        found.append(
            _INFO.finding(
                (function,),
                f"symbol {key!r} is not in the library ({where}{function_designation(laid, function)})",
            )
        )
    return tuple(found)
