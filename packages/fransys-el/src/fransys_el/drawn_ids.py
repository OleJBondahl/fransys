"""The ids of the page Drawing elements: the ids the retired `layout.drawn_*` records had (R234).

A Drawing lists its elements in `record_id_order` of these ids, so the bytes stay the same while
no record of those kinds exists. The stand-ins are no record: they hold only the kind text the
id is derived from.
"""

from fransys_model.kernel import make_id, render_id

__all__ = ["core_symbol_id", "lead_id", "symbol_id", "text_id", "wire_id"]

_KEY = ("layout", "core")


class _SymbolKind:
    __kind__ = "layout.drawn_symbol"


class _WireKind:
    __kind__ = "layout.drawn_wire"


class _TextKind:
    __kind__ = "layout.drawn_text"


def symbol_id(*key: str) -> str:
    """The render id of the symbol under `key`."""
    return render_id(make_id(_SymbolKind, key))


def core_symbol_id(sym: str) -> str:
    """The render id of the drawn symbol of core symbol `sym`."""
    return symbol_id(*_KEY, "drawn_symbol", sym)


def wire_id(number: int, net: str, index: int) -> str:
    """The render id of core wire `index` of drawing set `number`, on `net`."""
    key = (*_KEY, "drawn_wire", str(number), net, str(index))
    return render_id(make_id(_WireKind, key))


def text_id(kind: str, *subject: str) -> str:
    """The render id of the text of `kind` about `subject` (a symbol id)."""
    return render_id(make_id(_TextKind, (*_KEY, "drawn_text", kind, *subject)))


def lead_id(*key: str) -> str:
    """The render id of the wire under `key`: a lead no core wire holds, such as a power lead."""
    return render_id(make_id(_WireKind, key))
